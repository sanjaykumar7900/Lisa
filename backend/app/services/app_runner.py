import os
import re
import sys
import socket
import signal
import asyncio
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
import httpx

from app.core.config import settings
from app.core.security import validate_command, validate_startup_command

logger = logging.getLogger(__name__)


def find_free_port(start_port: Optional[int] = None, max_attempts: int = 500) -> int:
    """Finds an open TCP port on 127.0.0.1 starting from start_port."""
    base_port = start_port or settings.TARGET_PORT_RANGE_START or 3000
    for port in range(base_port, base_port + max_attempts):
        # Check both IPv4 and IPv6 if available
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            res = sock.connect_ex(('127.0.0.1', port))
            if res != 0:
                return port
    return base_port


class RuntimePortDiscovery:
    """
    Parses application runtime logs (stdout/stderr) to dynamically discover
    the active listening port or URL for various frameworks.
    """

    LOG_PATTERNS = [
        # Spring Boot / Tomcat / Netty / Jetty
        re.compile(r"Tomcat started on port\(s\):\s*(\d+)", re.I),
        re.compile(r"Netty started on port\s*(\d+)", re.I),
        re.compile(r"Started \w+ in \d+.*\(http://[^:]+:(\d+)", re.I),
        re.compile(r"EmbeddedServletContainer: .* port (\d+)", re.I),
        re.compile(r"Tomcat initialized with port\(s\):\s*(\d+)", re.I),

        # Vite / Next.js / Create React App / Webpack / Angular
        re.compile(r"Local:\s*(https?://[^\s]+)", re.I),
        re.compile(r"Network:\s*(https?://[^\s]+)", re.I),
        re.compile(r"ready in \d+ ms\s*(https?://[^\s]+)", re.I),
        re.compile(r"started server on [^,]+,\s*url:\s*(https?://[^\s]+)", re.I),
        re.compile(r"Server running on (https?://[^\s]+)", re.I),
        re.compile(r"Compiled successfully![\s\S]*?(https?://localhost:\d+)", re.I),
        re.compile(r"Project is running at\s*(https?://[^\s]+)", re.I),

        # Python / Flask / Django / FastAPI / Uvicorn
        re.compile(r"Running on (https?://[^\s]+)", re.I),
        re.compile(r"Running on http://(?:127\.0\.0\.1|localhost):(\d+)", re.I),
        re.compile(r"Uvicorn running on (https?://[^\s]+)", re.I),
        re.compile(r"Starting development server at (https?://[^\s/]+)", re.I),

        # Generic / Node / Express
        re.compile(r"Listening on (?:port\s*)?(\d+)", re.I),
        re.compile(r"Server listening on (?:port\s*)?(\d+)", re.I),
        re.compile(r"Serving HTTP on .* port (\d+)", re.I),
        re.compile(r"Server started on port (\d+)", re.I),
        re.compile(r"http://(?:localhost|127\.0\.0\.1):(\d+)", re.I),
    ]

    @classmethod
    def extract_url_or_port(cls, line: str) -> Optional[str]:
        """Extracts a full URL or port from a log line."""
        clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
        for pattern in cls.LOG_PATTERNS:
            match = pattern.search(clean_line)
            if match:
                val = match.group(1).rstrip('/')
                if val.isdigit():
                    return f"http://localhost:{val}"
                elif val.startswith("http://") or val.startswith("https://"):
                    # Normalize 0.0.0.0 to localhost
                    return val.replace("0.0.0.0", "localhost")
        return None


class ApplicationRunner:
    """
    Manages background process lifecycle for target open-source repositories being tested.
    Features dynamic runtime port discovery, fast crash detection, dual-stack health checking,
    and automatic static fallback.
    """

    def __init__(
        self,
        repo_dir: Path,
        startup_command: Optional[str] = None,
        target_port: Optional[int] = None,
        startup_timeout: Optional[float] = None
    ):
        self.repo_dir = repo_dir
        self.startup_command = startup_command
        self.target_port = target_port or settings.TARGET_APPLICATION_PORT or find_free_port(settings.TARGET_PORT_RANGE_START)
        self.startup_timeout = startup_timeout or settings.APP_STARTUP_TIMEOUT
        self.process: Optional[subprocess.Popen] = None
        self.fallback_process: Optional[subprocess.Popen] = None
        self.app_url: str = f"http://localhost:{self.target_port}"
        self.discovered_url: Optional[str] = None
        self.is_fallback: bool = False
        self.stdout_lines: List[str] = []
        self.stderr_lines: List[str] = []
        self._reader_tasks: List[asyncio.Task] = []

    async def start(self) -> Tuple[bool, str, bool, Optional[str], bool]:
        """
        Launches the target application with dynamic runtime discovery.
        Returns: (success: bool, app_url: str, is_fallback: bool, message: Optional[str], real_target_available: bool)
        """
        cmd = self.startup_command
        if not cmd:
            logger.info("No startup command specified. Launching static fallback server.")
            started, url, fallback, msg = await self._start_static_fallback("No startup command specified.")
            return started, url, fallback, msg, False

        cmd = self._use_target_port(cmd)

        # Validate security and internal state tokens
        is_valid, reason = validate_startup_command(cmd)
        if not is_valid:
            logger.warning(f"Startup command validation failed: {reason}. Launching static fallback server.")
            started, url, fallback, _ = await self._start_static_fallback(f"Startup command '{cmd}' rejected: {reason}")
            return started, url, fallback, f"Startup command '{cmd}' rejected: {reason}", False

        logger.info(f"Launching target application process: '{cmd}' in {self.repo_dir}")

        try:
            env = os.environ.copy()
            env["PORT"] = str(self.target_port)
            env["SERVER_PORT"] = str(self.target_port)
            env["HOST"] = "127.0.0.1"

            # Check if command executable exists before running
            cmd_root = cmd.strip().split()[0]
            if shutil_which := self._check_executable_exists(cmd_root):
                pass
            else:
                logger.warning(f"Executable '{cmd_root}' not found in PATH on system.")
                started, url, fallback, _ = await self._start_static_fallback(f"Executable '{cmd_root}' is not installed in system PATH.")
                return started, url, fallback, f"Executable '{cmd_root}' is not installed in system PATH.", False

            is_windows = os.name == "nt"
            preexec_fn = None if is_windows else os.setsid

            self.process = subprocess.Popen(
                cmd,
                shell=True,
                cwd=str(self.repo_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=preexec_fn,
                bufsize=1,
            )

            # Start background readers for stdout and stderr
            loop = asyncio.get_running_loop()
            self._reader_tasks = [
                loop.create_task(self._stream_reader(self.process.stdout, self.stdout_lines, "stdout")),
                loop.create_task(self._stream_reader(self.process.stderr, self.stderr_lines, "stderr")),
            ]

            # Poll for readiness with runtime port discovery and fast crash detection
            success, url_or_err = await self._wait_for_application_ready()
            if success:
                self.app_url = url_or_err
                logger.info(f"Target application successfully running at {self.app_url}")
                return True, self.app_url, False, None, True
            else:
                logger.warning(f"Target application failed to start: {url_or_err}. Falling back to static server.")
                self.stop()
                started, url, fallback, _ = await self._start_static_fallback(url_or_err)
                return started, url, fallback, url_or_err, False

        except Exception as e:
            logger.error(f"Error starting target application process: {e}")
            self.stop()
            started, url, fallback, _ = await self._start_static_fallback(str(e))
            return started, url, fallback, str(e), False

    def _check_executable_exists(self, cmd_name: str) -> bool:
        """Check if an executable or script is available in PATH or repo."""
        # Clean quotes
        clean_name = cmd_name.strip("\"'")
        if os.path.isabs(clean_name) or ("/" in clean_name) or ("\\" in clean_name):
            return (self.repo_dir / clean_name).exists() or Path(clean_name).exists()
        import shutil
        return shutil.which(clean_name) is not None

    async def _stream_reader(self, stream, output_list: List[str], label: str):
        """Asynchronously reads lines from a stream to avoid pipe buffer deadlocks and detect runtime ports."""
        if not stream:
            return
        loop = asyncio.get_running_loop()
        try:
            while True:
                line = await loop.run_in_executor(None, stream.readline)
                if not line:
                    break
                clean_line = line.strip()
                if clean_line:
                    output_list.append(clean_line)
                    # Check for runtime URL / port announcement
                    if not self.discovered_url:
                        found_url = RuntimePortDiscovery.extract_url_or_port(clean_line)
                        if found_url:
                            logger.info(f"Runtime port discovery detected URL from {label}: {found_url}")
                            self.discovered_url = found_url
        except Exception as e:
            logger.debug(f"Stream reader {label} terminated: {e}")

    async def _wait_for_application_ready(self) -> Tuple[bool, str]:
        """
        Polls the application until reachable via HTTP, checking both configured port
        and dynamically discovered runtime ports, while detecting early process crashes.
        """
        start_time = time.time()
        poll_interval = settings.APP_PORT_POLL_INTERVAL

        while time.time() - start_time < self.startup_timeout:
            # 1. Fast Process Death Check
            if self.process and self.process.poll() is not None:
                exit_code = self.process.returncode
                recent_stderr = "\n".join(self.stderr_lines[-10:]) if self.stderr_lines else ""
                recent_stdout = "\n".join(self.stdout_lines[-10:]) if self.stdout_lines else ""
                err_detail = recent_stderr or recent_stdout or f"Process exited with code {exit_code}"
                return False, f"Process terminated prematurely (exit code {exit_code}): {err_detail[:300]}"

            # 2. Check Discovered URL from logs if available
            candidate_urls = []
            if self.discovered_url:
                candidate_urls.append(self.discovered_url)

            # 3. Add default candidate URLs
            candidate_urls.extend([
                f"http://localhost:{self.target_port}",
                f"http://127.0.0.1:{self.target_port}"
            ])

            # Deduplicate preserving order
            seen = set()
            unique_candidates = []
            for u in candidate_urls:
                if u not in seen:
                    seen.add(u)
                    unique_candidates.append(u)

            # 4. Probe candidates
            for candidate in unique_candidates:
                is_ready = await self._check_url_ready(candidate)
                if is_ready:
                    return True, candidate

            await asyncio.sleep(poll_interval)

        # Timeout reached
        recent_stderr = "\n".join(self.stderr_lines[-5:]) if self.stderr_lines else ""
        return False, f"Application port polling timed out after {self.startup_timeout}s. {recent_stderr}".strip()

    async def _check_url_ready(self, url: str) -> bool:
        """Performs socket check and HTTP probe against candidate URL."""
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        # Step A: Rapid TCP socket connect
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                res = sock.connect_ex((host if host != "localhost" else "127.0.0.1", port))
                if res != 0:
                    return False
        except Exception:
            return False

        # Step B: HTTP GET probe (any status < 500 means server is alive and responding)
        try:
            async with httpx.AsyncClient(timeout=1.5, verify=False) as client:
                resp = await client.get(url)
                if resp.status_code < 500:
                    return True
                # Also test /health or /api if root gave 500
                health_resp = await client.get(f"{url.rstrip('/')}/health")
                if health_resp.status_code < 500:
                    return True
        except Exception:
            # Socket was open, so the server might be just finishing startup
            pass

        return False

    async def _start_static_fallback(self, reason: str = "") -> Tuple[bool, str, bool, str]:
        """
        Starts an internal Python HTTP server serving the repository's frontend or root directory.
        Guarantees a valid, reachable HTTP URL for automated testing.
        """
        self.is_fallback = True
        fallback_port = find_free_port(settings.TARGET_PORT_RANGE_START + 100)
        fallback_url = f"http://localhost:{fallback_port}"

        # Choose the best directory to serve
        static_dir = self._find_best_static_directory()
        logger.info(f"Starting static fallback server on {fallback_url} serving {static_dir}")

        cmd = f"{sys.executable} -m http.server {fallback_port} --directory \"{static_dir}\""

        try:
            is_windows = os.name == "nt"
            preexec_fn = None if is_windows else os.setsid

            self.fallback_process = subprocess.Popen(
                cmd,
                shell=True,
                cwd=str(self.repo_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=preexec_fn,
            )

            # Wait for fallback server to be reachable
            start_time = time.time()
            while time.time() - start_time < 5.0:
                if await self._check_url_ready(fallback_url):
                    self.app_url = fallback_url
                    logger.info(f"Static fallback server running at {self.app_url}")
                    return True, self.app_url, True, reason
                await asyncio.sleep(0.2)

            self.app_url = fallback_url
            return True, self.app_url, True, reason

        except Exception as e:
            logger.error(f"Failed to start static fallback server: {e}")
            self.app_url = fallback_url
            return False, self.app_url, True, f"Failed to start static fallback: {e}"

    def _find_best_static_directory(self) -> Path:
        """Finds the most relevant frontend/build/static directory in the repository."""
        candidates = [
            self.repo_dir / "frontend" / "dist",
            self.repo_dir / "frontend" / "build",
            self.repo_dir / "frontend" / "public",
            self.repo_dir / "frontend",
            self.repo_dir / "dist",
            self.repo_dir / "build",
            self.repo_dir / "public",
            self.repo_dir / "src" / "main" / "resources" / "static",
            self.repo_dir,
        ]
        for path in candidates:
            if path.exists() and path.is_dir():
                # Prefer directories with index.html or web assets
                if (path / "index.html").exists() or any(path.glob("*.html")):
                    return path
        for path in candidates:
            if path.exists() and path.is_dir():
                return path
        return self.repo_dir

    def _use_target_port(self, command: str) -> str:
        """Updates common server CLI flags with target port."""
        updated = re.sub(r"(--port|-p)\s+\d+", lambda match: f"{match.group(1)} {self.target_port}", command)
        updated = re.sub(r"(python(?:\.exe)?\s+-m\s+http\.server\s+)\d+", rf"\g<1>{self.target_port}", updated)
        updated = re.sub(r"(--server\.port=)\d+", rf"\g<1>{self.target_port}", updated)
        return updated

    def stop(self):
        """Terminates both primary and fallback application processes and stream readers."""
        for task in self._reader_tasks:
            if not task.done():
                task.cancel()
        self._reader_tasks.clear()

        for proc in [self.process, self.fallback_process]:
            if proc:
                pid = proc.pid
                logger.info(f"Stopping application process PID {pid}")
                try:
                    if os.name == "nt":
                        subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True, timeout=5)
                    else:
                        os.killpg(os.getpgid(pid), signal.SIGKILL)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

        self.process = None
        self.fallback_process = None

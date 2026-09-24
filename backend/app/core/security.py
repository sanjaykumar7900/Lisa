import os
import re
import shlex
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from typing import Tuple
from app.core.config import settings

SECRET_PATTERNS = [
    r'nvapi-[A-Za-z0-9_-]{30,}',  # NVIDIA API key
    r'ghp_[A-Za-z0-9]{36}',       # GitHub Personal Access Token
    r'github_pat_[A-Za-z0-9_]{22,}',
    r'sk-[A-Za-z0-9]{32,}',       # Generic secret key
    r'password=["\']?([^"\'\s&]+)["\']?',
    r'bearer\s+[A-Za-z0-9\-\._~\+\/]+=*',
]

# Hosts we are willing to clone from (prevents SSRF-style abuse).
ALLOWED_REPO_HOSTS = {"github.com", "gitlab.com", "bitbucket.org"}

# Destructive shell tokens that should never appear as a non-base argument.
FORBIDDEN_COMMAND_TOKENS = {
    "rm", "rmdir", "mkfs", "dd", "format", "shred", "wipe", "del",
    "shutdown", "reboot", "poweroff", "halt", "kill", "pkill",
    "chmod", "chown", "chattr", "mount", "umount",
    "curl", "wget", "nc", "ncat", "socat", "bash", "sh", "zsh", "fish",
}


# Structured error code constants for runtime status / dependency failures
MAVEN_MISSING = "MAVEN_MISSING"
MAVEN_WRAPPER_MISSING = "MAVEN_WRAPPER_MISSING"
JAVA_MISSING = "JAVA_MISSING"
NODE_MISSING = "NODE_MISSING"
NPM_MISSING = "NPM_MISSING"
PYTHON_MISSING = "PYTHON_MISSING"
DEPENDENCY_INSTALL_FAILED = "DEPENDENCY_INSTALL_FAILED"
STARTUP_COMMAND_NOT_FOUND = "STARTUP_COMMAND_NOT_FOUND"
STARTUP_FAILED = "STARTUP_FAILED"
PORT_NOT_REACHABLE = "PORT_NOT_REACHABLE"
HEALTH_CHECK_FAILED = "HEALTH_CHECK_FAILED"

# Internal runtime state/error tokens that must NEVER be passed as executable commands
INTERNAL_STATE_TOKENS = {
    "DEPENDENCY_MISSING",
    "MAVEN_MISSING",
    "MAVEN_WRAPPER_MISSING",
    "JAVA_MISSING",
    "NODE_MISSING",
    "NPM_MISSING",
    "PYTHON_MISSING",
    "STARTUP_COMMAND_NOT_FOUND",
    "STARTUP_FAILED",
    "PORT_NOT_REACHABLE",
    "HEALTH_CHECK_FAILED",
    "BLOCKED",
    "FAILED",
    "MISSING",
    "UNKNOWN",
    "NOT_STARTED",
    "STARTING",
    "READY",
}


def mask_secrets(text: str) -> str:
    """Replaces sensitive API keys, passwords, and tokens with masked strings."""
    if not text:
        return ""
    masked = text
    for pattern in SECRET_PATTERNS:
        masked = re.sub(pattern, '[REDACTED_SECRET]', masked, flags=re.IGNORECASE)
    return masked


def normalize_repo_url(url: str) -> str:
    """Return a clean cloneable URL stripping query params and tracking fragments."""
    cleaned = url.strip()
    if not cleaned:
        return cleaned
    # Strip everything after ? (tracking params like utm_source)
    cleaned = cleaned.split('?')[0]
    # Strip fragments
    cleaned = cleaned.split('#')[0]
    parsed = urlsplit(cleaned)
    if parsed.scheme and parsed.netloc:
        path = parsed.path.rstrip('/')
        cleaned = urlunsplit((parsed.scheme, parsed.netloc, path, '', ''))
    # Ensure .git suffix for GitHub URLs without it
    if ("github.com" in cleaned or "gitlab.com" in cleaned or "bitbucket.org" in cleaned) and not cleaned.endswith(".git"):
        cleaned += ".git"
    return cleaned


def validate_repo_url(url: str) -> Tuple[bool, str]:
    """Validates if the provided string is a valid HTTP/HTTPS Git repository URL."""
    url = normalize_repo_url(url)
    if not url:
        return False, "Repository URL cannot be empty."

    parsed = urlsplit(url if "://" in url else f"https://{url}")
    if parsed.scheme not in ("http", "https"):
        return False, "Repository URL must use http or https."
    if parsed.netloc not in ALLOWED_REPO_HOSTS:
        return False, (
            f"Repository host '{parsed.netloc}' is not allowed. "
            f"Allowed hosts: {', '.join(sorted(ALLOWED_REPO_HOSTS))}."
        )
    # Require a user/repo path component
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return False, "Repository URL must include a user and repository name."
    return True, "Valid repository URL."


def validate_startup_command(command: Optional[str]) -> Tuple[bool, str]:
    """
    Validation layer preceding process execution.
    Rejects null/empty commands and internal status/error tokens before
    checking the security allowlist.
    """
    if not command or not command.strip():
        return False, "No startup command specified."

    clean_cmd = command.strip()
    cmd_token = clean_cmd.split()[0].upper()

    if clean_cmd.upper() in INTERNAL_STATE_TOKENS or cmd_token in INTERNAL_STATE_TOKENS:
        return False, f"Command '{command}' represents an internal status/error token, not an executable command."

    return validate_command(clean_cmd)


def validate_command(command: str) -> Tuple[bool, str]:
    """Ensures the shell command uses only allowed CLI tools and contains no shell metacharacters.

    Uses ``shlex.split()`` so shell metacharacters (``;``, ``&&``, ``|``, ``>``, ``$()``,
    backticks, ``*``) cause a parse error rather than silently passing.
    """
    command_str = command.strip()
    if not command_str:
        return False, "Empty command."

    try:
        parts = shlex.split(command_str, posix=(os.name != 'nt'))
    except ValueError as e:
        return False, f"Command contains invalid shell syntax: {e}"

    if not parts:
        return False, "Empty command."

    raw_token = parts[0].strip("\"'")
    exe_name = Path(raw_token).name.lower()
    base_cmd = re.sub(r'\.exe$', '', exe_name)
    if base_cmd not in settings.ALLOWED_COMMANDS:
        return False, f"Command '{base_cmd}' is not in the security allowlist."

    # Reject any remaining shell metacharacters that shlex would have stripped
    # (defense in depth — shlex.split already handles most of these).
    dangerous_chars = [";", "&", "|", ">", "<", "$", "`", "\n", "\r"]
    for char in dangerous_chars:
        if char in command_str:
            return False, f"Forbidden shell character detected: '{char}'"

    # Reject destructive commands anywhere in the argument list
    for token in parts:
        token_lower = token.lower()
        if token_lower in FORBIDDEN_COMMAND_TOKENS and token_lower != base_cmd:
            return False, f"Forbidden command token detected: '{token}'"

    return True, "Command validation passed."


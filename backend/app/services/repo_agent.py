import os
import json
import logging
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
import git

from app.core.config import settings
from app.core.security import normalize_repo_url

logger = logging.getLogger(__name__)

class RepositoryAgent:
    """
    Autonomous Repository Agent responsible for cloning authorized GitHub repositories,
    inspecting the file system, reading README files, detecting package managers,
    build tools, language(s), frontend/backend frameworks, database usage, and startup commands.
    """

    def __init__(self, repo_url: str, project_id: str):
        self.repo_url = normalize_repo_url(repo_url)
        self.project_id = project_id
        self.clone_path = settings.TEMP_REPO_DIR / project_id

    def clone_repository(self) -> Path:
        """Clones or updates the target repository in a sandboxed directory."""
        if self.clone_path.exists():
            logger.info(f"Removing existing directory for re-clone: {self.clone_path}")
            shutil.rmtree(self.clone_path, ignore_errors=True)

        self.clone_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cloning {self.repo_url} into {self.clone_path}")
        
        # Try GitPython first
        try:
            git.Repo.clone_from(self.repo_url, str(self.clone_path), depth=1)
        except Exception as git_e:
            # Try appending .git for bare URLs
            url_with_git = self.repo_url if self.repo_url.endswith(".git") else self.repo_url + ".git"
            if url_with_git != self.repo_url:
                try:
                    git.Repo.clone_from(url_with_git, str(self.clone_path), depth=1)
                    return self.clone_path
                except Exception:
                    pass
            # Fallback: subprocess with explicit output
            logger.warning(f"GitPython clone failed for {self.repo_url}: {git_e}")
            try:
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", self.repo_url, str(self.clone_path)],
                    check=True, capture_output=True, text=True, timeout=90
                )
            except subprocess.CalledProcessError as sub_e:
                msg = f"Failed to fetch repo from {self.repo_url}. stderr: {sub_e.stderr or 'none'} stdout: {sub_e.stdout or 'none'}. Ensure URL is public/valid."
                logger.error(msg)
                raise RuntimeError(msg)
            except Exception as sub_e:
                msg = f"Failed to fetch repo from {self.repo_url}: {sub_e}"
                logger.error(msg)
                raise RuntimeError(msg)

        return self.clone_path

    def analyze(self) -> Dict[str, Any]:
        """Inspect the repository recursively and return evidence-backed QA metadata."""
        if not self.clone_path.exists() or not any(self.clone_path.iterdir()):
            self.clone_repository()

        ignored = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".next", "target"}
        MAX_FILE_SIZE = 1_000_000  # 1 MB — skip binary / very large files

        def _safe_iter():
            """Yield files up to the configured limit, skipping large / excluded paths."""
            count = 0
            for p in self.clone_path.rglob("*"):
                if count >= settings.MAX_REPO_FILES:
                    logger.warning("Hit MAX_REPO_FILES (%d); stopping file scan.", settings.MAX_REPO_FILES)
                    break
                if p.is_file() and not any(part in ignored for part in p.parts):
                    try:
                        if p.stat().st_size > MAX_FILE_SIZE:
                            continue
                    except OSError:
                        continue
                    count += 1
                    yield p

        files = list(_safe_iter())
        rel = lambda path: path.relative_to(self.clone_path).as_posix()
        evidence: Dict[str, List[str]] = {}
        add_evidence = lambda key, paths: evidence.setdefault(key, []).extend(sorted({rel(p) for p in paths}))
        languages = set()
        startup_commands: List[str] = []
        ports: List[Dict[str, Any]] = []
        packages = [p for p in files if p.name == "package.json"]
        vite_files = [p for p in files if p.name.startswith("vite.config.")]
        java_files = [p for p in files if p.suffix == ".java"]
        pom_files = [p for p in files if p.name == "pom.xml"]
        gradle_files = [p for p in files if p.name in {"build.gradle", "build.gradle.kts"}]
        prop_files = [p for p in files if p.name in {"application.properties", "application.yml", "application.yaml"}]
        readmes = [p for p in files if p.name.lower() in {"readme.md", "readme.rst", "readme.txt"}]
        readme_content = readmes[0].read_text(encoding="utf-8", errors="ignore")[:5000] if readmes else ""

        frontend = None
        backend = None
        database = None
        orm = None
        build_tools: List[str] = []
        package_manager = None
        test_framework = None
        api_available = False
        route_count = 0
        api_count = 0
        api_endpoints: List[Dict[str, Any]] = []

        runtime_status = "NOT_STARTED"
        dependency_status = "AVAILABLE"
        failure_reason = None

        for package_file in packages:
            try:
                package = json.loads(package_file.read_text(encoding="utf-8", errors="ignore"))
            except json.JSONDecodeError:
                continue
            deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
            if "react" in deps or "react-dom" in deps:
                frontend = "React" + (" + Vite" if vite_files else "")
                languages.update({"JavaScript"} if not any(p.name == "tsconfig.json" for p in files) else {"TypeScript"})
                add_evidence("frontend", [package_file] + vite_files + [p for p in files if p.suffix in {".jsx", ".tsx"}])
            if "vite" in deps or vite_files:
                frontend = "React + Vite" if "react" in deps or "react-dom" in deps else "Vite"
                add_evidence("frontend", [package_file] + vite_files)
            for name in ("express", "fastify", "@nestjs/core"):
                if name in deps:
                    backend = {"express": "Express.js", "fastify": "Fastify", "@nestjs/core": "NestJS"}[name]
                    api_available = True
            if "vitest" in deps or "jest" in deps or "@playwright/test" in deps:
                test_framework = "vitest" if "vitest" in deps else ("jest" if "jest" in deps else "playwright")
            if package_file.parent == self.clone_path or not package_manager:
                package_manager = "yarn" if (package_file.parent / "yarn.lock").exists() else ("pnpm" if (package_file.parent / "pnpm-lock.yaml").exists() else "npm")
            build_tools.append(package_manager)
            scripts = package.get("scripts", {})
            if scripts.get("dev"):
                if package_file.parent == self.clone_path:
                    startup_commands.append(f"{package_manager} run dev")
                else:
                    rel_dir = rel(package_file.parent)
                    startup_commands.append(f"{package_manager} --prefix {rel_dir} run dev")
                ports.append({"name": "Frontend", "technology": frontend or "Node.js", "port": 5173, "source": rel(package_file) + " scripts.dev"})

        pom_text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in pom_files).lower()
        gradle_text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in gradle_files).lower()
        if pom_files or gradle_files or java_files:
            languages.add("Java")
            build_tools.append("Maven" if pom_files else "Gradle")
            if "spring-boot" in pom_text or "springframework.boot" in gradle_text or any("@springbootapplication" in p.read_text(encoding="utf-8", errors="ignore").lower() for p in java_files):
                backend = "Java + Spring Boot"
                api_available = True
                add_evidence("backend", pom_files + [p for p in java_files if "@springbootapplication" in p.read_text(encoding="utf-8", errors="ignore").lower() or "@restcontroller" in p.read_text(encoding="utf-8", errors="ignore").lower()])
                
                wrapper_file = next((p for p in files if p.name in {"mvnw", "mvnw.cmd"}), None)
                has_mvn_cli = shutil.which("mvn") is not None
                has_java_cli = shutil.which("java") is not None

                if wrapper_file:
                    mvn_cmd = "mvnw.cmd" if (os.name == "nt" or wrapper_file.name == "mvnw.cmd") else "./mvnw"
                elif has_mvn_cli:
                    mvn_cmd = "mvn"
                else:
                    mvn_cmd = None

                if not has_java_cli:
                    runtime_status = "BLOCKED"
                    dependency_status = "MISSING"
                    failure_reason = "JAVA_MISSING"
                    logger.warning("[DISCOVERY] Java dependency missing for Spring Boot project")
                elif not mvn_cmd:
                    runtime_status = "BLOCKED"
                    dependency_status = "MISSING"
                    failure_reason = "MAVEN_MISSING"
                    logger.warning("[DISCOVERY] Maven dependency missing for Spring Boot project")
                else:
                    startup_commands.append(f"{mvn_cmd} spring-boot:run")
                ports.append({"name": "Backend", "technology": backend, "port": 8080, "source": "Spring Boot default; inspect application config"})
            if "spring-boot-starter-data-jpa" in pom_text or "spring-data-jpa" in gradle_text or any("@entity" in p.read_text(encoding="utf-8", errors="ignore").lower() for p in java_files):
                orm = "JPA / Hibernate"
                add_evidence("orm", pom_files + [p for p in java_files if "@entity" in p.read_text(encoding="utf-8", errors="ignore").lower()])
            if "mysql-connector" in pom_text or "mysql" in gradle_text:
                database = "MySQL"
                add_evidence("database", pom_files + prop_files)
        python_files = [p for p in files if p.suffix == ".py"]
        req_files = [p for p in files if p.name.startswith("requirements") and p.suffix == ".txt"]
        pyproject_files = [p for p in files if p.name == "pyproject.toml"]
        setup_files = [p for p in files if p.name == "setup.py"]
        if python_files or req_files or pyproject_files or setup_files:
            languages.add("Python")
            package_manager = package_manager or "pip"
            python_text = "\n".join(p.read_text(encoding="utf-8", errors="ignore").lower() for p in req_files + pyproject_files)
            if "fastapi" in python_text:
                backend = "FastAPI"
                api_available = True
            elif "django" in python_text:
                backend = "Django"
                api_available = True
            elif "flask" in python_text:
                backend = "Flask"
                api_available = True
            if "pytest" in python_text or any(p.name == "pytest.ini" for p in files):
                test_framework = "pytest"
            if "mysql" in python_text:
                database = "MySQL"
            elif "postgres" in python_text or "psycopg" in python_text:
                database = "PostgreSQL"
            elif "sqlite" in python_text:
                database = "SQLite"
            entry_points = [p for p in python_files if p.name in {"main.py", "app.py", "server.py"}]
            if not startup_commands and entry_points and runtime_status != "BLOCKED":
                entry_point = min(entry_points, key=lambda path: len(path.parts))
                startup_commands.append(f"python {rel(entry_point)}")
            add_evidence("backend", python_files[:30] + req_files + pyproject_files)
        config_text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in prop_files)
        mysql_match = re.search(r"jdbc:mysql://[^:/]+:(\d+)", config_text, re.I)
        if mysql_match:
            ports.append({"name": "Database", "technology": "MySQL", "port": int(mysql_match.group(1)), "source": rel(next(p for p in prop_files if "jdbc:mysql" in p.read_text(encoding="utf-8", errors="ignore")))})
            database = "MySQL"
        if "server.port" in config_text:
            match = re.search(r"server\.port\s*[=:]\s*(\d+)", config_text)
            if match:
                ports = [{**port, "port": int(match.group(1))} if port["name"] == "Backend" else port for port in ports]
        add_evidence("database", prop_files if database else [])
        if not languages:
            languages.add("JavaScript")
        if not startup_commands and runtime_status != "BLOCKED":
            startup_commands.append("python -m http.server 3000")
        add_evidence("routes", [p for p in files if p.suffix in {".jsx", ".tsx", ".js", ".java"}])
        for java_file in java_files:
            java_text = java_file.read_text(encoding="utf-8", errors="ignore")
            class_prefix_match = re.search(r"@RequestMapping\(\s*\"([^\"]+)\"\s*\).*?class\s+", java_text, re.S)
            class_prefix = class_prefix_match.group(1).rstrip("/") if class_prefix_match else ""
            for match in re.finditer(r"@(Get|Post|Put|Delete|Patch)Mapping(?:\(\s*(?:\"([^\"]*)\")?\s*\))?", java_text):
                path = f"{class_prefix}/{match.group(2) or ''}".replace("//", "/") or "/"
                if path != "/":
                    path = path.rstrip("/")
                api_endpoints.append({"method": match.group(1).upper(), "path": path, "evidence": [rel(java_file)]})
        route_count = sum(len(re.findall(r"react-router|Route\s|@GetMapping|@PostMapping|@PutMapping|@DeleteMapping", p.read_text(encoding="utf-8", errors="ignore"))) for p in files if p.suffix in {".jsx", ".tsx", ".js", ".java"})
        api_count = sum(len(re.findall(r"fetch\(|axios\.|@(?:Get|Post|Put|Delete|Request)Mapping", p.read_text(encoding="utf-8", errors="ignore"))) for p in files if p.suffix in {".jsx", ".tsx", ".js", ".java"})
        modules = []
        for item in sorted([p for p in self.clone_path.iterdir() if p.is_dir() and p.name not in ignored and not p.name.startswith(".")]):
            module_files = [p for p in files if item in p.parents]
            content = "\n".join(p.read_text(encoding="utf-8", errors="ignore")[:10000] for p in module_files if p.suffix in {".java", ".js", ".jsx", ".ts", ".tsx"})
            role = "Static Assets"
            if "react" in content.lower() or any(p.name.startswith("vite.config") for p in module_files): role = "React + Vite Frontend"
            elif any("@restcontroller" in p.read_text(encoding="utf-8", errors="ignore").lower() for p in module_files if p.suffix == ".java"): role = "Spring Boot Backend"
            modules.append({"name": item.name, "path": item.name, "files_count": len(module_files), "role": role, "routes_count": len(re.findall(r"react-router|Route\s", content)), "components_count": len(re.findall(r"function\s+\w+|const\s+\w+\s*=\s*\(", content)), "controllers_count": len(re.findall(r"@RestController", content)), "services_count": len(re.findall(r"@Service", content)), "repositories_count": len(re.findall(r"@Repository|extends\s+JpaRepository", content)), "api_count": len(re.findall(r"fetch\(|axios\.|@(?:Get|Post|Put|Delete|Request)Mapping", content)), "sample_files": [p.name for p in module_files[:10]]})
        if not modules:
            modules.append({"name": "Core Application", "path": ".", "files_count": len(files), "role": frontend or backend or "Application", "routes_count": route_count, "api_count": api_count, "sample_files": [p.name for p in files[:10]]})
        architecture = [{"label": frontend, "technology": frontend, "evidence": evidence.get("frontend", [])}] if frontend else []
        if api_available: architecture.append({"label": "REST API", "technology": "HTTP endpoints", "evidence": evidence.get("backend", [])})
        if backend: architecture.append({"label": backend, "technology": backend, "evidence": evidence.get("backend", [])})
        if orm: architecture.append({"label": orm, "technology": orm, "evidence": evidence.get("orm", [])})
        if database: architecture.append({"label": database, "technology": database, "evidence": evidence.get("database", [])})
        return {
            "languages": sorted(languages),
            "frontend": frontend or "Not detected",
            "backend": backend or ("Python" if "Python" in languages else "Not detected"),
            "database": database or "Not detected",
            "orm": orm or "Not detected",
            "build_tool": " + ".join(dict.fromkeys(build_tools)) or "Not detected",
            "package_manager": package_manager or "Not detected",
            "test_framework": test_framework or "Not detected",
            "api_available": api_available,
            "application_type": "web" if frontend else "service",
            "startup_commands": startup_commands,
            "startup_command": startup_commands[0] if startup_commands else None,
            "runtime_status": runtime_status,
            "dependency_status": dependency_status,
            "failure_reason": failure_reason,
            "ports": ports,
            "evidence": evidence,
            "architecture": architecture,
            "route_count": route_count,
            "api_count": api_count,
            "api_endpoints": api_endpoints,
            "modules": modules,
            "readme_snippet": readme_content[:1000]
        }

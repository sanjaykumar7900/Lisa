"""Universal runtime discovery with evidence provenance. Framework defaults are low-confidence only."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.discovery.endpoint_registry import EndpointRegistry
from app.core.discovery.service_topology import ServiceTopology

FRAMEWORK_DEFAULTS = {
    "spring": {"port": 8080, "confidence": 0.20, "source": "spring_default"},
    "react_cra": {"port": 3000, "confidence": 0.20, "source": "cra_default"},
    "vite": {"port": 5173, "confidence": 0.20, "source": "vite_default"},
    "fastapi": {"port": 8000, "confidence": 0.20, "source": "fastapi_default"},
    "flask": {"port": 5000, "confidence": 0.20, "source": "flask_default"},
    "django": {"port": 8000, "confidence": 0.20, "source": "django_default"},
}

PORT_MAP = re.compile(r"""['\"]?(\d+)\s*:\s*(\d+)['\"]?""")
SERVER_PORT_PROP = re.compile(r"server\.port\s*[=:]\s*(\d+)", re.I)
ENV_PORT = re.compile(r"^\s*(?:SERVER_PORT|PORT)\s*[=:]\s*(\d+)", re.I | re.M)
JDBC_PG = re.compile(r"jdbc:postgresql://([^:/]+):?(\d+)?/([^\s]+)", re.I)
JDBC_MYSQL = re.compile(r"jdbc:mysql://([^:/]+):?(\d+)?/([^\s]+)", re.I)
MONGO_URI = re.compile(r"mongodb(?:\+srv)?://", re.I)
SQLITE = re.compile(r"jdbc:sqlite:|sqlite:///|\.sqlite", re.I)


class RuntimeDiscovery:
    """Discovers services, ports, databases, and startup evidence from a repository tree."""

    def discover(self, repo_url: str | Path, repo_dir: Optional[Path] = None) -> Dict[str, Any]:
        path = Path(repo_dir or repo_url)
        if not path.exists():
            return {"repo": str(repo_url), "services": [], "ports": {}, "confidence": {}, "status": "DISCOVERING"}
        files = [p for p in path.rglob("*") if p.is_file()]
        ignored = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", "target"}
        files = [p for p in files if not any(part in ignored for part in p.parts)]

        services: List[Dict[str, Any]] = []
        evidence: List[Dict[str, Any]] = []
        database: Dict[str, Any] = {}
        compose_ports = self._docker_compose_ports(path, files)

        frontend = self._discover_frontend(path, files, compose_ports)
        if frontend:
            services.append(frontend)
            evidence.append({"property": "frontend", **{k: frontend[k] for k in ("port", "source", "confidence") if k in frontend}})

        backend = self._discover_backend(path, files, compose_ports)
        if backend:
            services.append(backend)
            evidence.append({"property": "backend", **{k: backend[k] for k in ("port", "source", "confidence") if k in backend}})

        database = self._discover_database(path, files)
        if database:
            services.append(
                {
                    "name": "database",
                    "type": "database",
                    "technology": database.get("type"),
                    "port": (database.get("port") or {}).get("value") if isinstance(database.get("port"), dict) else database.get("port"),
                    "source": database.get("source"),
                    "confidence": database.get("confidence", 0.5),
                    "dependencies": [],
                }
            )

        registry = EndpointRegistry()
        endpoints = registry.discover(path, files)
        topology = ServiceTopology.build(services, database)

        ports = {}
        confidence = {}
        for svc in services:
            if svc.get("port"):
                ports[svc.get("name")] = {
                    "value": svc.get("host_port") or svc.get("port"),
                    "container_port": svc.get("container_port"),
                    "source": svc.get("source"),
                    "confidence": svc.get("confidence"),
                }
                confidence[f"{svc.get('name')}_port"] = svc.get("confidence")

        return {
            "repo": str(repo_url),
            "services": services,
            "ports": ports,
            "database": database,
            "topology": topology,
            "endpoints": endpoints,
            "confidence": confidence,
            "evidence": evidence,
            "status": "DISCOVERED",
        }

    def _rel(self, repo: Path, file: Path) -> str:
        try:
            return file.relative_to(repo).as_posix()
        except ValueError:
            return file.name

    def _docker_compose_ports(self, repo: Path, files: List[Path]) -> List[Dict[str, Any]]:
        results = []
        compose_files = [p for p in files if p.name in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}]
        for compose in compose_files:
            text = compose.read_text(encoding="utf-8", errors="ignore")
            current = None
            for raw_line in text.splitlines():
                line = raw_line.split("#")[0].rstrip()
                svc = re.match(r"^  ([A-Za-z0-9._-]+):\s*$", line)
                if svc:
                    current = svc.group(1)
                    continue
                if current:
                    mapped = PORT_MAP.search(line)
                    if mapped and ("ports" in line or line.strip().startswith("-") or mapped):
                        if PORT_MAP.search(line) and re.search(r"\d+:\d+", line):
                            host_port, container_port = int(mapped.group(1)), int(mapped.group(2))
                            results.append(
                                {
                                    "service": current,
                                    "host_port": host_port,
                                    "container_port": container_port,
                                    "source": self._rel(repo, compose),
                                    "confidence": 0.95,
                                }
                            )
                    env_port = ENV_PORT.search(line)
                    if env_port:
                        results.append(
                            {
                                "service": current,
                                "host_port": int(env_port.group(1)),
                                "container_port": None,
                                "source": self._rel(repo, compose) + " env",
                                "confidence": 0.85,
                            }
                        )
        return results

    def _compose_match(self, compose_ports: List[Dict[str, Any]], keywords: List[str]) -> Optional[Dict[str, Any]]:
        for item in compose_ports:
            blob = json.dumps(item).lower()
            if any(k in item.get("service", "").lower() or k in blob for k in keywords):
                return item
        return None

    def _discover_frontend(self, repo: Path, files: List[Path], compose_ports: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        packages = [p for p in files if p.name == "package.json"]
        for package_file in packages:
            try:
                package = json.loads(package_file.read_text(encoding="utf-8", errors="ignore"))
            except json.JSONDecodeError:
                continue
            deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
            scripts = package.get("scripts") or {}
            name = None
            default_key = None
            if "react-scripts" in deps or "react-scripts" in json.dumps(scripts):
                name, default_key = "React / Create React App", "react_cra"
            elif "next" in deps:
                name, default_key = "Next.js", "react_cra"
            elif "vite" in deps or any(p.name.startswith("vite.config") for p in files):
                name, default_key = "React + Vite" if "react" in deps else "Vite", "vite"
            elif "vue" in deps:
                name, default_key = "Vue", "vite"
            elif "angular" in json.dumps(deps):
                name, default_key = "Angular", "vite"
            elif "react" in deps or "react-dom" in deps:
                name, default_key = "React", "react_cra"
            if not name:
                continue
            mapped = self._compose_match(compose_ports, ["frontend", "ui", "web", "react"])
            port_info = self._port_from_scripts(scripts) or {}
            if mapped:
                port = mapped["host_port"]
                source = mapped["source"]
                confidence = mapped["confidence"]
                container = mapped.get("container_port")
            elif port_info:
                port, source, confidence, container = port_info["port"], self._rel(repo, package_file), 0.8, None
            else:
                default = FRAMEWORK_DEFAULTS[default_key]
                port, source, confidence, container = default["port"], default["source"], default["confidence"], None
            startup = None
            manager = "npm"
            if (package_file.parent / "yarn.lock").exists():
                manager = "yarn"
            rel_dir = self._rel(repo, package_file.parent)
            prefix = "" if rel_dir in {".", ""} else f"--prefix {rel_dir} "
            if scripts.get("start"):
                startup = f"{manager} {prefix}start".replace("  ", " ")
            elif scripts.get("dev"):
                startup = f"{manager} {prefix}run dev".replace("  ", " ")
            return {
                "name": "frontend",
                "type": "frontend",
                "technology": name,
                "port": port,
                "host_port": port,
                "container_port": container,
                "protocol": "http",
                "startup_command": startup,
                "source": source,
                "confidence": confidence,
                "dependencies": ["backend"] if any(True for _ in [1]) else [],
                "health_state": "UNKNOWN",
            }
        html = [p for p in files if p.suffix == ".html"]
        if html:
            return {
                "name": "frontend",
                "type": "frontend",
                "technology": "static HTML",
                "port": None,
                "protocol": "http",
                "source": self._rel(repo, html[0]),
                "confidence": 0.4,
                "dependencies": [],
                "health_state": "UNKNOWN",
            }
        return None

    def _port_from_scripts(self, scripts: Dict[str, str]) -> Optional[Dict[str, Any]]:
        blob = json.dumps(scripts)
        match = re.search(r"--port(?:\s|=)(\d+)", blob)
        if match:
            return {"port": int(match.group(1))}
        match = re.search(r"PORT=(\d+)", blob)
        if match:
            return {"port": int(match.group(1))}
        return None

    def _discover_backend(self, repo: Path, files: List[Path], compose_ports: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        pom = [p for p in files if p.name == "pom.xml"]
        gradle = [p for p in files if p.name in {"build.gradle", "build.gradle.kts"}]
        java = [p for p in files if p.suffix == ".java"]
        props = [p for p in files if p.name in {"application.properties", "application.yml", "application.yaml"}]
        mapped = self._compose_match(compose_ports, ["backend", "api", "spring", "app", "server"])

        port = None
        source = None
        confidence = 0.0
        container = None
        if mapped:
            port, source, confidence, container = mapped["host_port"], mapped["source"], mapped["confidence"], mapped.get("container_port")

        for prop in props:
            text = prop.read_text(encoding="utf-8", errors="ignore")
            match = SERVER_PORT_PROP.search(text)
            if match:
                config_port = int(match.group(1))
                if not mapped:
                    port, source, confidence, container = config_port, self._rel(repo, prop), 0.98, None
                else:
                    container = container or config_port
                    source = f"{source}; {self._rel(repo, prop)}"
                break

        technology = None
        startup = None
        if pom or gradle or java:
            pom_text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in pom).lower()
            if "spring-boot" in pom_text or any("@SpringBootApplication" in p.read_text(encoding="utf-8", errors="ignore") for p in java[:50]):
                technology = "Spring Boot / Java / Maven" if pom else "Spring Boot / Java / Gradle"
                if port is None:
                    default = FRAMEWORK_DEFAULTS["spring"]
                    port, source, confidence = default["port"], default["source"], default["confidence"]
                wrapper = next((p for p in files if p.name in {"mvnw", "mvnw.cmd"}), None)
                if wrapper:
                    startup = "mvnw.cmd spring-boot:run" if os.name == "nt" or wrapper.name == "mvnw.cmd" else "./mvnw spring-boot:run"
                elif pom:
                    startup = "mvn spring-boot:run"
                elif gradle:
                    startup = "./gradlew bootRun"

        python_files = [p for p in files if p.suffix == ".py"]
        req = [p for p in files if p.name.startswith("requirements") and p.suffix == ".txt"]
        if not technology and (python_files or req):
            req_text = "\n".join(p.read_text(encoding="utf-8", errors="ignore").lower() for p in req)
            if "fastapi" in req_text:
                technology = "FastAPI"
                default = FRAMEWORK_DEFAULTS["fastapi"]
            elif "django" in req_text:
                technology = "Django"
                default = FRAMEWORK_DEFAULTS["django"]
            elif "flask" in req_text:
                technology = "Flask"
                default = FRAMEWORK_DEFAULTS["flask"]
            else:
                technology = "Python"
                default = None
            if port is None and default:
                port, source, confidence = default["port"], default["source"], default["confidence"]
            entry = next((p for p in python_files if p.name in {"main.py", "app.py", "server.py"}), None)
            if entry:
                startup = f"python {self._rel(repo, entry)}"

        packages = [p for p in files if p.name == "package.json"]
        for package_file in packages:
            try:
                package = json.loads(package_file.read_text(encoding="utf-8", errors="ignore"))
            except json.JSONDecodeError:
                continue
            deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
            if "express" in deps:
                technology = technology or "Express"
            elif "@nestjs/core" in deps:
                technology = technology or "NestJS"

        if not technology and port is None:
            return None
        return {
            "name": "backend",
            "type": "backend",
            "technology": technology or "API service",
            "port": port,
            "host_port": port,
            "container_port": container,
            "protocol": "http",
            "startup_command": startup,
            "source": source,
            "confidence": confidence,
            "dependencies": ["database"],
            "health_state": "UNKNOWN",
        }

    def _discover_database(self, repo: Path, files: List[Path]) -> Dict[str, Any]:
        props = [p for p in files if p.name in {"application.properties", "application.yml", "application.yaml", ".env", "docker-compose.yml", "docker-compose.yaml", "compose.yml"}]
        compose_files = [p for p in files if p.name in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}]
        text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in props + compose_files)
        rel_source = self._rel(repo, (props or compose_files or files)[0]) if (props or compose_files or files) else "unknown"
        if JDBC_PG.search(text) or re.search(r"image:\s*postgres", text, re.I) or "postgresql" in text.lower():
            port_match = re.search(r"(\d+):5432", text)
            host_port = int(port_match.group(1)) if port_match else None
            jdbc = JDBC_PG.search(text)
            return {
                "type": "PostgreSQL",
                "port": {"value": host_port or (int(jdbc.group(2)) if jdbc and jdbc.group(2) else 5432), "source": rel_source, "confidence": 0.9 if host_port or jdbc else 0.4},
                "source": rel_source,
                "confidence": 0.92 if host_port or jdbc else 0.55,
                "evidence": [rel_source],
            }
        if JDBC_MYSQL.search(text) or re.search(r"image:\s*mysql|mariadb", text, re.I):
            return {"type": "MySQL", "source": rel_source, "confidence": 0.9, "evidence": [rel_source]}
        if MONGO_URI.search(text) or re.search(r"image:\s*mongo", text, re.I):
            return {"type": "MongoDB", "source": rel_source, "confidence": 0.9, "evidence": [rel_source]}
        if SQLITE.search(text):
            return {"type": "SQLite", "source": rel_source, "confidence": 0.85, "evidence": [rel_source]}
        return {}

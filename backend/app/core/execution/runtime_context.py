from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


PLACEHOLDER_HOSTS = {"example.com", "www.example.com", "example.org", "www.example.org"}
PLACEHOLDER_PATHS = {"/frontend", "/src/items", "/api/health"}


@dataclass
class Provenance:
    value: Any
    source: str
    confidence: float

    def as_dict(self) -> Dict[str, Any]:
        return {"value": self.value, "source": self.source, "confidence": self.confidence}


@dataclass
class RuntimeContext:
    """Single authoritative runtime view consumed by every execution agent."""

    frontend_base_url: str = ""
    backend_base_url: str = ""
    api_base_url: str = ""
    runtime_context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    services: List[Dict[str, Any]] = field(default_factory=list)
    database: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[Dict[str, Any]] = field(default_factory=list)
    health: Dict[str, Any] = field(default_factory=dict)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    confidence: Dict[str, float] = field(default_factory=dict)
    real_target_available: bool = False
    is_fallback: bool = False
    runtime_status: str = "NOT_STARTED"
    discovered_endpoints: List[Dict[str, Any]] = field(default_factory=list)

    def allowed_hosts(self) -> set[str]:
        hosts = set()
        for url in (self.frontend_base_url, self.backend_base_url, self.api_base_url):
            host = urlparse(url).netloc
            if host:
                hosts.add(host)
        for service in self.services:
            url = service.get("base_url") or ""
            host = urlparse(url).netloc
            if host:
                hosts.add(host)
        return hosts

    def validate_target_url(self, url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        target = urlparse(url)
        if not target.scheme or not target.netloc:
            return False
        host = (target.hostname or "").lower()
        if host in PLACEHOLDER_HOSTS:
            return False
        allowed = self.allowed_hosts()
        if not allowed:
            return False
        if self.is_fallback:
            return False
        if not self.real_target_available:
            return host and host in {x.lower() for x in allowed}
        return bool(target.netloc) and target.netloc in allowed

    def service_base_url(self, service_name: str) -> Optional[str]:
        wanted = (service_name or "").lower()
        for service in self.services:
            name = str(service.get("name") or "").lower()
            stype = str(service.get("type") or "").lower()
            if wanted in {name, stype} or wanted in name:
                return service.get("base_url")
        if wanted in {"backend", "api"}:
            return self.api_base_url or self.backend_base_url
        if wanted in {"frontend", "ui"}:
            return self.frontend_base_url
        return None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "runtime_context_id": self.runtime_context_id,
            "frontend_base_url": self.frontend_base_url,
            "backend_base_url": self.backend_base_url,
            "api_base_url": self.api_base_url,
            "services": self.services,
            "database": self.database,
            "dependencies": self.dependencies,
            "health": self.health,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "real_target_available": self.real_target_available,
            "is_fallback": self.is_fallback,
            "runtime_status": self.runtime_status,
        }

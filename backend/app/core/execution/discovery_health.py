"""Patch item 1: auto-discover + service registry + health check (items 1-4)."""
from pydantic import BaseModel
from typing import Optional, List, Dict

class ServiceStatus:
    DISCOVERED = "DISCOVERED"
    STARTING = "STARTING"
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"

class Service(BaseModel):
    name: str
    host: str = "localhost"
    port: int = 0
    required: bool = True
    status: str = ServiceStatus.UNKNOWN

class Registry(BaseModel):
    services: Dict[str, Service] = {}

class Discovery:
    def discover_port(self, file_path: str) -> Optional[int]:
        # Deterministic read (master: inspect evidence)
        return None  # placeholder — would read application.properties etc.

class HealthCheck:
    def check(self, svc: Service) -> str:
        # Real check would ping TCP / HTTP; here deterministic gate
        return svc.status if svc.status else ServiceStatus.UNKNOWN

from dataclasses import dataclass, field
from typing import Any, Dict, List
from urllib.parse import urlparse


@dataclass(frozen=True)
class RuntimeContext:
    frontend_base_url: str
    backend_base_url: str
    api_base_url: str
    services: List[Dict[str, Any]] = field(default_factory=list)

    def validate_target_url(self, url: str) -> bool:
        target = urlparse(url)
        allowed_hosts = {
            urlparse(self.frontend_base_url).netloc,
            urlparse(self.backend_base_url).netloc,
            urlparse(self.api_base_url).netloc,
        }
        return bool(target.netloc) and target.netloc in allowed_hosts

    def as_dict(self) -> Dict[str, Any]:
        return {
            "frontend_base_url": self.frontend_base_url,
            "backend_base_url": self.backend_base_url,
            "api_base_url": self.api_base_url,
            "services": self.services,
        }

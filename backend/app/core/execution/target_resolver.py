"""Validate and construct execution URLs from RuntimeContext + contracts."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse

from app.core.execution.runtime_context import PLACEHOLDER_HOSTS, PLACEHOLDER_PATHS, RuntimeContext

logger = logging.getLogger(__name__)

UNRESOLVED_TOKEN = re.compile(r"\{[^}/]+\}")
INVENTED_GENERIC = {"/api/health", "/frontend", "/src/items"}


@dataclass
class TargetResolution:
    accepted: bool
    url: str = ""
    reason: str = ""
    service: str = ""


class TargetResolver:
    @staticmethod
    def resolve(
        path_or_url: str,
        runtime: RuntimeContext,
        *,
        service: str = "backend",
        endpoint_id: Optional[str] = None,
        discovered_paths: Optional[set[str]] = None,
    ) -> TargetResolution:
        raw = (path_or_url or "").strip()
        if not raw:
            return TargetResolution(False, reason="Empty target path")

        if UNRESOLVED_TOKEN.search(raw):
            reason = f"Unresolved path parameter in target: {raw}"
            logger.info("[TARGET] rejected %s (%s)", raw, reason)
            return TargetResolution(False, reason=reason, service=service)

        if raw.startswith("http://") or raw.startswith("https://"):
            parsed = urlparse(raw)
            host = (parsed.hostname or "").lower()
            if host in PLACEHOLDER_HOSTS or host == "example.com":
                reason = f"Target URL is outside the current runtime topology: {raw}"
                logger.info("[TARGET] rejected %s (%s)", raw, reason)
                return TargetResolution(False, reason=reason, service=service)
            if not runtime.validate_target_url(raw):
                reason = f"Target URL is outside the current runtime topology: {raw}"
                logger.info("[TARGET] rejected %s (%s)", raw, reason)
                return TargetResolution(False, reason=reason, service=service)
            return TargetResolution(True, url=raw, reason="Absolute URL matches RuntimeContext", service=service)

        normalized = raw if raw.startswith("/") else f"/{raw}"
        if normalized.rstrip("/") in PLACEHOLDER_PATHS or normalized.rstrip("/") in INVENTED_GENERIC:
            allowed = discovered_paths or {
                (item.get("path") or "").rstrip("/")
                for item in runtime.discovered_endpoints
            }
            if normalized.rstrip("/") not in allowed:
                reason = f"Placeholder/invented path rejected without repository evidence: {normalized}"
                logger.info("[TARGET] rejected %s (%s)", normalized, reason)
                return TargetResolution(False, reason=reason, service=service)

        if not runtime.real_target_available or runtime.is_fallback:
            reason = "Real target application is not available"
            logger.info("[TARGET] rejected %s (%s)", normalized, reason)
            return TargetResolution(False, reason=reason, service=service)

        base = runtime.service_base_url(service) or runtime.api_base_url or runtime.backend_base_url
        if not base:
            reason = f"No base URL in RuntimeContext for service '{service}'"
            logger.info("[TARGET] rejected %s (%s)", normalized, reason)
            return TargetResolution(False, reason=reason, service=service)

        full = urljoin(base.rstrip("/") + "/", normalized.lstrip("/"))
        if not runtime.validate_target_url(full):
            reason = f"Constructed URL failed topology validation: {full}"
            logger.info("[TARGET] rejected %s (%s)", full, reason)
            return TargetResolution(False, reason=reason, service=service)

        logger.info("[TARGET] accepted %s via %s", full, service)
        return TargetResolution(True, url=full, reason="Resolved from RuntimeContext", service=service)

    @staticmethod
    def production_code_allows_example_com(text: str) -> bool:
        return "https://example.com" in text or "http://example.com" in text

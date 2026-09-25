"""Layered health checks. GET / is not automatically healthy."""

from __future__ import annotations

import socket
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.core.execution.status_model import HealthLayer


class HealthEngine:
    @staticmethod
    def tcp_listening(host: str, port: int, timeout: float = 0.5) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                return sock.connect_ex((host if host != "localhost" else "127.0.0.1", port)) == 0
        except OSError:
            return False

    @staticmethod
    async def probe(
        url: str,
        *,
        health_path: Optional[str] = None,
        process_running: bool = False,
    ) -> Dict[str, Any]:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        layers = {
            HealthLayer.PROCESS_RUNNING.value: process_running,
            HealthLayer.PORT_LISTENING.value: HealthEngine.tcp_listening(host, port),
            HealthLayer.PROTOCOL_READY.value: False,
            HealthLayer.APPLICATION_HEALTHY.value: False,
        }
        if not layers[HealthLayer.PORT_LISTENING.value]:
            return {"url": url, "layers": layers, "healthy": False, "reason": "PORT_NOT_REACHABLE"}

        try:
            async with httpx.AsyncClient(timeout=2.0, verify=False) as client:
                if health_path:
                    resp = await client.get(url.rstrip("/") + health_path)
                    layers[HealthLayer.PROTOCOL_READY.value] = True
                    layers[HealthLayer.APPLICATION_HEALTHY.value] = 200 <= resp.status_code < 500
                    return {"url": url, "layers": layers, "healthy": layers[HealthLayer.APPLICATION_HEALTHY.value], "status_code": resp.status_code, "reason": None}
                resp = await client.get(url)
                layers[HealthLayer.PROTOCOL_READY.value] = resp.status_code < 500
                # A document or API root responding is protocol-ready, not automatically application-healthy.
                layers[HealthLayer.APPLICATION_HEALTHY.value] = False
                return {
                    "url": url,
                    "layers": layers,
                    "healthy": layers[HealthLayer.PROTOCOL_READY.value],
                    "status_code": resp.status_code,
                    "reason": None,
                    "note": "APPLICATION_HEALTHY requires an evidence-backed health endpoint",
                }
        except Exception as exc:
            return {"url": url, "layers": layers, "healthy": False, "reason": str(exc)}

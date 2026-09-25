"""Discover HTTP endpoints from source, OpenAPI, and frontend clients. Never invent routes."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

SPRING_CLASS_MAPPING = re.compile(r"@RequestMapping\(\s*(?:value\s*=\s*)?\"([^\"]+)\"", re.S)
SPRING_METHOD = re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping(?:\s*\(\s*(?:(?:value|path)\s*=\s*)?\"([^\"]*)\")?", re.I)
SPRING_RESPONSE = re.compile(r"@ResponseStatus\([^)]*(?:HttpStatus\.)?([A-Z_]+|\d{3})")
FASTAPI_ROUTE = re.compile(r"@(?:app|router)\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']", re.I)
FLASK_ROUTE = re.compile(r"@app\.route\(\s*[\"']([^\"']+)[\"'](?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?", re.I)
EXPRESS_ROUTE = re.compile(r"(?:app|router)\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']", re.I)
NEST_ROUTE = re.compile(r"@(Get|Post|Put|Delete|Patch)\(\s*[\"']([^\"']*)[\"']", re.I)
NEST_CONTROLLER = re.compile(r"@Controller\(\s*[\"']([^\"']+)[\"']")
FETCH_CALL = re.compile(r"fetch\(\s*[`'\"]([^`'\"]+)", re.I)
AXIOS_CALL = re.compile(r"axios\.(get|post|put|delete|patch)\(\s*[`'\"]([^`'\"]+)", re.I)
HTTP_STATUS_NAME = {
    "OK": 200,
    "CREATED": 201,
    "ACCEPTED": 202,
    "NO_CONTENT": 204,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "INTERNAL_SERVER_ERROR": 500,
}


class EndpointRegistry:
    def __init__(self) -> None:
        self.endpoints: List[Dict[str, Any]] = []

    def discover(self, repo_dir: Path, files: Optional[List[Path]] = None) -> List[Dict[str, Any]]:
        files = files or [p for p in repo_dir.rglob("*") if p.is_file()]
        ignored = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".next", "target"}
        files = [p for p in files if not any(part in ignored for part in p.parts)]
        self.endpoints = []
        for path in files:
            rel = path.relative_to(repo_dir).as_posix() if path.is_relative_to(repo_dir) else path.name
            suffix = path.suffix.lower()
            name = path.name.lower()
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if suffix == ".java":
                self._spring(text, rel)
            elif suffix == ".py":
                self._fastapi(text, rel)
                self._flask(text, rel)
            elif suffix in {".js", ".ts", ".jsx", ".tsx"}:
                self._express(text, rel)
                self._nest(text, rel)
                self._frontend_clients(text, rel)
            if name in {"openapi.json", "swagger.json"}:
                self._openapi_json(text, rel)
            if name.endswith((".yaml", ".yml")) and "openapi" in text[:200].lower():
                self._openapi_yaml_paths(text, rel)
        return self.deduped()

    def deduped(self) -> List[Dict[str, Any]]:
        seen = set()
        out = []
        for item in self.endpoints:
            key = (item.get("method"), (item.get("path") or "").rstrip("/") or "/")
            if key in seen:
                continue
            seen.add(key)
            item["endpoint_id"] = f"http_{key[0].lower()}:{key[1]}"
            out.append(item)
        return out

    def known_paths(self) -> set[str]:
        return {(item.get("path") or "").rstrip("/") or "/" for item in self.deduped()}

    def _add(self, method: str, path: str, source: str, confidence: float, expected_status: Optional[int] = None) -> None:
        cleaned = EndpointRegistry._normalize_path(path)
        if not cleaned:
            return
        self.endpoints.append(
            {
                "method": method.upper(),
                "path": cleaned,
                "source": source,
                "evidence": [source],
                "confidence": confidence,
                "expected_status": expected_status,
                "service": "backend",
            }
        )

    @staticmethod
    def _normalize_path(path: str) -> str:
        if not path:
            return ""
        path = path.strip()
        if path.startswith("http"):
            from urllib.parse import urlparse
            path = urlparse(path).path or "/"
        if "${" in path or path.startswith("process.env"):
            return ""
        if not path.startswith("/"):
            path = "/" + path
        path = re.sub(r"/+", "/", path)
        if path != "/":
            path = path.rstrip("/")
        return path

    def _spring(self, text: str, source: str) -> None:
        prefix_match = SPRING_CLASS_MAPPING.search(text)
        prefix = prefix_match.group(1).rstrip("/") if prefix_match else ""
        for match in SPRING_METHOD.finditer(text):
            method = match.group(1).upper()
            suffix = match.group(2) or ""
            path = f"{prefix}/{suffix}".replace("//", "/") or "/"
            expected = EndpointRegistry._nearby_status(text, match.start())
            self._add(method, path, source, 0.99, expected)

    def _fastapi(self, text: str, source: str) -> None:
        for match in FASTAPI_ROUTE.finditer(text):
            self._add(match.group(1), match.group(2), source, 0.98)

    def _flask(self, text: str, source: str) -> None:
        for match in FLASK_ROUTE.finditer(text):
            methods = match.group(2)
            path = match.group(1)
            if methods:
                for method in re.findall(r"[A-Z]+", methods.upper()):
                    self._add(method, path, source, 0.96)
            else:
                self._add("GET", path, source, 0.9)

    def _express(self, text: str, source: str) -> None:
        for match in EXPRESS_ROUTE.finditer(text):
            self._add(match.group(1), match.group(2), source, 0.95)

    def _nest(self, text: str, source: str) -> None:
        ctrl = NEST_CONTROLLER.search(text)
        prefix = ctrl.group(1).rstrip("/") if ctrl else ""
        for match in NEST_ROUTE.finditer(text):
            self._add(match.group(1), f"{prefix}/{match.group(2)}", source, 0.97)

    def _frontend_clients(self, text: str, source: str) -> None:
        for match in FETCH_CALL.finditer(text):
            path = EndpointRegistry._normalize_path(match.group(1))
            if path and ("/api" in path or path.startswith("/v")):
                self._add("GET", path, source, 0.55)
        for match in AXIOS_CALL.finditer(text):
            path = EndpointRegistry._normalize_path(match.group(2))
            if path:
                self._add(match.group(1), path, source, 0.6)

    def _openapi_json(self, text: str, source: str) -> None:
        try:
            spec = json.loads(text)
        except json.JSONDecodeError:
            return
        paths = spec.get("paths") or {}
        for path, ops in paths.items():
            if not isinstance(ops, dict):
                continue
            for method, op in ops.items():
                if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                    continue
                expected = None
                responses = (op or {}).get("responses") if isinstance(op, dict) else None
                if isinstance(responses, dict):
                    codes = [int(k) for k in responses if str(k).isdigit()]
                    if codes:
                        expected = sorted(codes)[0]
                self._add(method, path, source, 0.97, expected)

    def _openapi_yaml_paths(self, text: str, source: str) -> None:
        for match in re.finditer(r"^\s{2}(/[^\s:]+):", text, re.M):
            self._add("GET", match.group(1), source, 0.5)

    @staticmethod
    def _nearby_status(text: str, index: int) -> Optional[int]:
        window = text[max(0, index - 400) : index + 400]
        match = SPRING_RESPONSE.search(window)
        if not match:
            return None
        token = match.group(1)
        if token.isdigit():
            return int(token)
        return HTTP_STATUS_NAME.get(token)

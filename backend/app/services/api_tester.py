import json
import logging
import time
from typing import Any, Dict, Tuple
from urllib.parse import urlparse
import httpx
from app.core.execution.runtime_context import RuntimeContext

logger = logging.getLogger(__name__)

class APITester:
    """
    Automated HTTP API testing agent for GET, POST, PUT, PATCH, DELETE endpoints.
    """

    @staticmethod
    async def execute_api_test(step: Dict[str, Any], base_url: str | RuntimeContext) -> Tuple[bool, str, float]:
        if isinstance(base_url, RuntimeContext):
            runtime_context = base_url
            base_url = runtime_context.api_base_url
        else:
            runtime_context = None
        method = step.get("action", "http_get").upper().replace("HTTP_", "")
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            return False, f"Invalid test method: {method}", 0.0
        endpoint = step.get("target", "/")
        full_url = endpoint if endpoint.startswith("http") else f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        base_host = urlparse(base_url).netloc
        target_host = urlparse(full_url).netloc
        if (runtime_context and not runtime_context.validate_target_url(full_url)) or target_host != base_host:
            return False, f"Invalid test target: {full_url} is outside the current runtime {base_url}", 0.0
        
        headers = step.get("headers", {"Content-Type": "application/json"})
        payload = step.get("value")
        
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "GET":
                    response = await client.get(full_url, headers=headers)
                elif method == "POST":
                    json_body = json.loads(payload) if payload and isinstance(payload, str) else payload
                    response = await client.post(full_url, headers=headers, json=json_body)
                elif method == "PUT":
                    json_body = json.loads(payload) if payload and isinstance(payload, str) else payload
                    response = await client.put(full_url, headers=headers, json=json_body)
                elif method == "PATCH":
                    json_body = json.loads(payload) if payload and isinstance(payload, str) else payload
                    response = await client.patch(full_url, headers=headers, json=json_body)
                elif method == "DELETE":
                    response = await client.delete(full_url, headers=headers)
                else:
                    response = await client.get(full_url, headers=headers)

                duration = time.time() - start_time
                expected = (step.get("expected") or "").lower()
                if "below 500" in expected:
                    is_success = response.status_code < 500
                elif "status 2" in expected or "http 200" in expected:
                    is_success = 200 <= response.status_code < 300
                elif "4xx" in expected:
                    is_success = 400 <= response.status_code < 500
                else:
                    is_success = response.status_code < 400
                msg = f"HTTP {method} {full_url} -> Status {response.status_code} ({duration:.2f}s)"
                return is_success, msg, duration

        except Exception as e:
            duration = time.time() - start_time
            return False, f"HTTP {method} {full_url} failed: {str(e)}", duration

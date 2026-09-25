import json
import logging
import time
from typing import Any, Dict, Tuple
import httpx

from app.core.execution.assertion_engine import AssertionEngine
from app.core.execution.parameter_resolver import ParameterResolver, TestDataStore
from app.core.execution.pass_authority import PassAuthority
from app.core.execution.runtime_context import RuntimeContext
from app.core.execution.target_resolver import TargetResolver
from app.core.execution.test_contract import TestContractEngine
from app.core.security import mask_secrets

logger = logging.getLogger(__name__)


class APITester:
    """HTTP API testing agent. Never executes invalid/placeholder/unresolved targets."""

    def __init__(self, data_store: TestDataStore | None = None):
        self.data_store = data_store or TestDataStore()
        self.resolver = ParameterResolver(self.data_store)
        self.assertions = AssertionEngine()

    @staticmethod
    async def execute_api_test(step: Dict[str, Any], base_url: str | RuntimeContext) -> Tuple[bool, str, float]:
        tester = APITester()
        result = await tester.execute_step(step, base_url)
        return result["passed"], result["message"], result["duration"]

    async def execute_step(self, step: Dict[str, Any], base_url: str | RuntimeContext) -> Dict[str, Any]:
        if isinstance(base_url, RuntimeContext):
            runtime = base_url
        else:
            runtime = RuntimeContext(frontend_base_url=base_url, backend_base_url=base_url, api_base_url=base_url, real_target_available=True)

        method = step.get("action", "http_get").upper().replace("HTTP_", "")
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            decision = PassAuthority.decide(valid_target=True, valid_contract=False, executed=False, contract_reason=f"Invalid test method: {method}")
            return {"passed": False, "message": decision.reason, "duration": 0.0, "status": decision.status, "result_validity": decision.result_validity, "executed": False, "assertions": []}

        raw_path = step.get("target", "/")
        resolved_path, missing = self.resolver.resolve_path(raw_path)
        if missing:
            decision = PassAuthority.decide(valid_target=True, valid_contract=True, executed=False, unresolved_parameters=True, contract_reason=f"Unresolved required parameter(s): {', '.join(missing)}")
            return {"passed": False, "message": decision.reason, "duration": 0.0, "status": decision.status, "result_validity": decision.result_validity, "executed": False, "assertions": []}

        target = TargetResolver.resolve(resolved_path, runtime, service="backend")
        if not target.accepted:
            decision = PassAuthority.decide(valid_target=False, valid_contract=True, executed=False, target_reason=target.reason)
            return {"passed": False, "message": decision.reason, "duration": 0.0, "status": decision.status, "result_validity": decision.result_validity, "executed": False, "assertions": []}

        expected_status = TestContractEngine.parse_expected_status(str(step.get("expected") or ""))
        assertions_spec = step.get("assertions") or ([] if expected_status is None else [{"type": "status_code", "expected": expected_status}])
        if not assertions_spec:
            decision = PassAuthority.decide(valid_target=True, valid_contract=True, executed=False, assertions=[], contract_reason="No valid assertion")
            # If we still executed nothing because assertions are missing, do not send the request.
            return {"passed": False, "message": "No valid assertion — request not treated as PASS", "duration": 0.0, "status": "UNVERIFIED", "result_validity": "UNVERIFIED", "executed": False, "assertions": []}

        headers = step.get("headers") or {"Content-Type": "application/json"}
        payload = self.resolver.resolve_value(step.get("value"))
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                json_body = None
                if payload is not None and method in {"POST", "PUT", "PATCH"}:
                    json_body = json.loads(payload) if isinstance(payload, str) else payload
                response = await client.request(method, target.url, headers=headers, json=json_body)
                duration = time.time() - start_time
                body_text = response.text[:4000]
                json_data = None
                try:
                    json_data = response.json()
                    self.data_store.ingest_response(json_data)
                except Exception:
                    json_data = None
                assertion_results = self.assertions.evaluate(
                    assertions_spec,
                    {"status_code": response.status_code, "headers": dict(response.headers), "json": json_data or {}, "body": body_text},
                )
                decision = PassAuthority.decide(
                    valid_target=True,
                    valid_contract=True,
                    executed=True,
                    assertions=assertion_results,
                )
                msg = mask_secrets(f"HTTP {method} {target.url} -> Status {response.status_code} ({duration:.2f}s)")
                return {
                    "passed": decision.status == "PASSED",
                    "message": msg,
                    "duration": duration,
                    "status": decision.status,
                    "result_validity": decision.result_validity,
                    "executed": True,
                    "assertions": [item.as_dict() for item in assertion_results],
                    "request": {"method": method, "url": target.url, "body": json_body},
                    "response": {"status_code": response.status_code, "body": mask_secrets(body_text)},
                    "target_url": target.url,
                }
        except Exception as exc:
            duration = time.time() - start_time
            reason = str(exc)
            token = "TIMEOUT" if "timeout" in reason.lower() else "NETWORK_FAILURE"
            return {
                "passed": False,
                "message": mask_secrets(f"HTTP {method} {target.url} failed: {reason}"),
                "duration": duration,
                "status": "FAILED",
                "result_validity": "VALID",
                "executed": True,
                "failure_reason": token,
                "assertions": [],
            }

"""Executable Test Contract — required before any application test runs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.execution.parameter_resolver import ParameterResolver
from app.core.execution.runtime_context import RuntimeContext
from app.core.execution.target_resolver import TargetResolver

WEAK_ASSERTIONS = (
    "below 500",
    "no exception",
    "request returned",
    "http request returned",
    "status 2",
)


@dataclass
class TestContract:
    test_id: str
    test_type: str
    target_service: str
    method: str
    path: str
    resolved_url: str = ""
    endpoint_id: str = ""
    evidence_sources: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    runtime_context_id: str = ""
    valid: bool = False
    invalid_reason: str = ""
    status: str = "NOT_STARTED"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "test_type": self.test_type,
            "target_service": self.target_service,
            "method": self.method,
            "path": self.path,
            "resolved_url": self.resolved_url,
            "endpoint_id": self.endpoint_id,
            "evidence_sources": self.evidence_sources,
            "preconditions": self.preconditions,
            "actions": self.actions,
            "assertions": self.assertions,
            "runtime_context_id": self.runtime_context_id,
            "valid": self.valid,
            "invalid_reason": self.invalid_reason,
        }


class TestContractEngine:
    @staticmethod
    def from_case(
        test_id: str,
        test_type: str,
        steps: List[Dict[str, Any]],
        runtime: RuntimeContext,
        resolver: ParameterResolver,
        *,
        target_service: str = "backend",
        evidence_sources: Optional[List[str]] = None,
        discovered_paths: Optional[set[str]] = None,
        expected_result: str = "",
        test_data: Optional[Dict[str, Any]] = None,
    ) -> TestContract:
        normalized_steps: List[Dict[str, Any]] = [
            s.model_dump() if hasattr(s, "model_dump") else (s.dict() if hasattr(s, "dict") else s)
            for s in steps
        ]
        evidence_sources = evidence_sources or list((test_data or {}).get("evidence_sources") or [])
        endpoint_id = str((test_data or {}).get("endpoint_id") or "")
        first_http = next((s for s in normalized_steps if str(s.get("action") or "").lower().startswith("http_")), None)
        method = (first_http.get("action") or "http_get").replace("http_", "").upper() if first_http else "GET"
        raw_path = (first_http.get("target") if first_http else (normalized_steps[0].get("target") if normalized_steps else "/")) or "/"
        resolved_path, missing = resolver.resolve_path(raw_path)

        assertions = TestContractEngine._assertions_from_steps(normalized_steps, method, expected_result)
        if not assertions and isinstance((test_data or {}).get("expected_status"), int):
            assertions.append({"type": "status_code", "expected": test_data["expected_status"]})

        contract = TestContract(
            test_id=test_id,
            test_type=test_type,
            target_service=target_service if test_type == "api" else "frontend",
            method=method,
            path=resolved_path,
            endpoint_id=endpoint_id or f"{method.lower()}:{resolved_path}",
            evidence_sources=evidence_sources,
            assertions=assertions,
            runtime_context_id=runtime.runtime_context_id,
            actions=normalized_steps,
        )

        if missing:
            contract.invalid_reason = f"Unresolved required parameter(s): {', '.join(missing)}"
            contract.status = "BLOCKED"
            return contract

        if not assertions:
            contract.invalid_reason = "Test contract has no executable assertions"
            contract.status = "UNVERIFIED"
            return contract

        if any(TestContractEngine._is_weak(a) for a in assertions) and not any(
            a.get("type") == "status_code" and isinstance(a.get("expected"), int) for a in assertions
        ):
            contract.invalid_reason = "Weak assertion is not sufficient for a PASS (HTTP 2xx / below 500)"
            return contract

        if test_type == "api":
            target = TargetResolver.resolve(
                resolved_path,
                runtime,
                service=contract.target_service,
                discovered_paths=discovered_paths,
            )
            if not target.accepted:
                contract.invalid_reason = target.reason
                contract.status = "INVALID_TARGET" if "Placeholder" in target.reason or "outside" in target.reason else "BLOCKED"
                return contract
            contract.resolved_url = target.url

        contract.valid = True
        return contract

    @staticmethod
    def _is_weak(assertion: Dict[str, Any]) -> bool:
        blob = f"{assertion.get('type')} {assertion.get('expected')}".lower()
        return any(token in blob for token in WEAK_ASSERTIONS)

    @staticmethod
    def _assertions_from_steps(steps: List[Dict[str, Any]], method: str, expected_result: str) -> List[Dict[str, Any]]:
        assertions: List[Dict[str, Any]] = []
        for step in steps:
            step_dict = step.model_dump() if hasattr(step, "model_dump") else (step.dict() if hasattr(step, "dict") else step)
            step_status = step_dict.get("expected_status") if isinstance(step_dict.get("expected_status"), int) else None
            if step_status is None:
                step_status = TestContractEngine.parse_expected_status(str(step_dict.get("expected") or ""))
            if step_status is not None:
                status_assertion = {"type": "status_code", "expected": step_status}
                if status_assertion not in assertions:
                    assertions.append(status_assertion)
            if step_dict.get("assertions"):
                for a in step_dict["assertions"]:
                    if a not in assertions:
                        assertions.append(a)
        if not assertions:
            parsed = TestContractEngine.parse_expected_status(expected_result)
            if parsed is not None:
                status_assertion = {"type": "status_code", "expected": parsed}
                if status_assertion not in assertions:
                    assertions.append(status_assertion)
        return assertions

    @staticmethod
    def parse_expected_status(text: str) -> Optional[int]:
        if not text:
            return None
        lowered = text.lower()
        if "below 500" in lowered or "status 2" in lowered:
            return None
        match = re.search(r"\b(?:status(?:_code)?\s*(?:==|=|is|:|is exactly|exactly)?\s*)?(?:http\s*)?(\d{3})\b", lowered)
        if match:
            return int(match.group(1))
        return None

"""Phase 1 — Test Oracle (API assertions)."""
from pydantic import BaseModel, Field
from typing import Any, Optional, List

class AssertionEvidence(BaseModel):
    assertion: str
    expected: Any
    actual: Any
    passed: bool = False
    evidence: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

class APIOracle:
    def assert_status(self, response, expected: int) -> AssertionEvidence:
        actual = getattr(response, "status_code", response.get("status") if isinstance(response, dict) else None)
        passed = actual == expected
        return AssertionEvidence(
            assertion="status_code",
            expected=expected, actual=actual, passed=passed,
            evidence=f"HTTP {actual}", confidence=0.99 if passed else 0.0
        )

    def assert_json_schema(self, response, required: List[str]) -> AssertionEvidence:
        data = response.json() if hasattr(response, "json") else response.get("data", response)
        missing = [k for k in required if k not in data]
        passed = len(missing) == 0
        return AssertionEvidence(
            assertion="json_required_fields",
            expected=required, actual=list(data.keys()) if isinstance(data, dict) else data,
            passed=passed, evidence=f"missing={missing}" if missing else "all present",
            confidence=0.94 if passed else 0.5
        )

"""Deterministic assertion engine. LLM output is never the PASS authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AssertionResult:
    assertion_type: str
    expected: Any
    actual: Any
    passed: bool
    executed: bool = True
    evidence: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "type": self.assertion_type,
            "expected": self.expected,
            "actual": self.actual,
            "passed": self.passed,
            "executed": self.executed,
            "evidence": self.evidence,
        }


class AssertionEngine:
    def evaluate(self, assertions: List[Dict[str, Any]], context: Dict[str, Any]) -> List[AssertionResult]:
        results: List[AssertionResult] = []
        for spec in assertions or []:
            results.append(self._eval_one(spec, context))
        return results

    def _eval_one(self, spec: Dict[str, Any], context: Dict[str, Any]) -> AssertionResult:
        kind = str(spec.get("type") or spec.get("assertion") or "").lower()
        expected = spec.get("expected")
        if kind in {"status_code", "status"}:
            actual = context.get("status_code")
            passed = actual == expected
            return AssertionResult(kind, expected, actual, passed, evidence=f"HTTP {actual}")
        if kind in {"header", "headers"}:
            headers = {str(k).lower(): v for k, v in (context.get("headers") or {}).items()}
            name = str(spec.get("name") or spec.get("key") or "").lower()
            actual = headers.get(name)
            passed = str(actual) == str(expected) if actual is not None else False
            return AssertionResult(kind, expected, actual, passed, evidence=f"{name}={actual}")
        if kind in {"json_field", "json_value"}:
            data = context.get("json") if isinstance(context.get("json"), dict) else {}
            field_name = spec.get("field") or spec.get("path")
            actual = data.get(field_name) if field_name else None
            passed = actual == expected
            return AssertionResult(kind, expected, actual, passed, evidence=f"{field_name}={actual}")
        if kind in {"json_required_fields", "required_fields"}:
            data = context.get("json") if isinstance(context.get("json"), dict) else {}
            required = expected if isinstance(expected, list) else spec.get("fields") or []
            missing = [k for k in required if k not in data]
            return AssertionResult(kind, required, list(data.keys()), not missing, evidence=f"missing={missing}")
        if kind in {"page_title", "title"}:
            actual = context.get("title")
            passed = bool(actual) if expected in (None, "", "The page has a title") else str(expected) in str(actual)
            return AssertionResult(kind, expected, actual, passed, evidence=f"title={actual}")
        if kind in {"url"}:
            actual = context.get("url")
            passed = str(expected) in str(actual) if expected else bool(actual)
            return AssertionResult(kind, expected, actual, passed, evidence=f"url={actual}")
        if kind in {"element_visible"}:
            actual = bool(context.get("visible"))
            return AssertionResult(kind, True, actual, actual is True, evidence=f"visible={actual}")
        return AssertionResult(kind or "unknown", expected, None, False, executed=False, evidence="Unknown assertion type")

    @staticmethod
    def all_passed(results: List[AssertionResult]) -> bool:
        executed = [r for r in results if r.executed]
        return bool(executed) and all(r.passed for r in executed)

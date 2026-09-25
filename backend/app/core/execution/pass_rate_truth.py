"""Truthful pass-rate: only VALID executed PASS+FAIL tests."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from app.core.execution.status_model import EXCLUDED_FROM_PASS_RATE, ExecutionStatus


class PassRateTruth:
    VALID_EXECUTED = {ExecutionStatus.PASSED.value, ExecutionStatus.FAILED.value}

    @staticmethod
    def compute(passed: int, failed: int, error: int = 0, blocked: int = 0) -> Optional[float]:
        # error/blocked never enter the denominator, even if callers pass them.
        executed = passed + failed
        if executed == 0:
            return None
        return round((passed / executed) * 100, 2)

    @staticmethod
    def format(rate: Optional[float]) -> str:
        return "N/A" if rate is None else f"{rate:.2f}%"

    @staticmethod
    def from_results(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        rows = list(results)
        statuses = [str(item.get("status") or "") for item in rows]
        passed = statuses.count(ExecutionStatus.PASSED.value)
        failed = statuses.count(ExecutionStatus.FAILED.value)
        blocked = statuses.count(ExecutionStatus.BLOCKED.value)
        invalid = statuses.count(ExecutionStatus.INVALID_TEST.value) + statuses.count(ExecutionStatus.INVALID_TARGET.value)
        unverified = statuses.count(ExecutionStatus.UNVERIFIED.value)
        infra = statuses.count(ExecutionStatus.INFRASTRUCTURE_FAILURE.value)
        skipped = statuses.count(ExecutionStatus.SKIPPED.value)
        flaky = statuses.count(ExecutionStatus.FLAKY.value)
        rate = PassRateTruth.compute(passed, failed)
        return {
            "total": len(rows),
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "invalid": invalid,
            "unverified": unverified,
            "infrastructure_failures": infra,
            "skipped": skipped,
            "flaky": flaky,
            "executed": passed + failed,
            "pass_rate": rate,
            "pass_rate_display": PassRateTruth.format(rate),
            "excluded_from_denominator": sorted(EXCLUDED_FROM_PASS_RATE),
        }

"""Retry with per-attempt evidence. A retry is not a new test."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

RETRYABLE = {"TIMEOUT", "NETWORK_FAILURE", "ENVIRONMENT_FAILURE", "INFRASTRUCTURE_FAILURE"}


@dataclass
class AttemptRecord:
    test_id: str
    execution_id: str
    attempt_number: int
    timestamp: str
    target: str
    request: Dict[str, Any]
    response: Dict[str, Any]
    evidence: Dict[str, Any]
    failure_reason: str
    status: str


@dataclass
class RetryOutcome:
    status: str
    attempts: List[AttemptRecord] = field(default_factory=list)
    flaky: bool = False


class RetryLogic:
    def __init__(self, max_attempts: int = 3) -> None:
        self.max_attempts = max_attempts

    def should_retry(self, failure_reason: str, attempt_number: int) -> bool:
        if attempt_number >= self.max_attempts:
            return False
        token = (failure_reason or "").upper()
        return any(code in token for code in RETRYABLE)

    async def run(
        self,
        test_id: str,
        execution_id: str,
        operation: Callable[[int], Awaitable[Dict[str, Any]]],
    ) -> RetryOutcome:
        attempts: List[AttemptRecord] = []
        statuses: List[str] = []
        for attempt in range(1, self.max_attempts + 1):
            payload = await operation(attempt)
            record = AttemptRecord(
                test_id=test_id,
                execution_id=execution_id,
                attempt_number=attempt,
                timestamp=str(payload.get("timestamp") or ""),
                target=str(payload.get("target") or ""),
                request=payload.get("request") or {},
                response=payload.get("response") or {},
                evidence=payload.get("evidence") or {},
                failure_reason=str(payload.get("failure_reason") or ""),
                status=str(payload.get("status") or ""),
            )
            attempts.append(record)
            statuses.append(record.status)
            if record.status == "PASSED":
                break
            if not self.should_retry(record.failure_reason or record.status, attempt):
                break
        unique = set(statuses)
        flaky = "PASSED" in unique and any(s == "FAILED" for s in unique)
        final = "FLAKY" if flaky else statuses[-1]
        return RetryOutcome(status=final, attempts=attempts, flaky=flaky)

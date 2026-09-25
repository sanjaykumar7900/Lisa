"""Single PASS authority. No shortcuts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.core.execution.assertion_engine import AssertionResult
from app.core.execution.status_model import ExecutionStatus, ResultValidity


@dataclass
class PassDecision:
    status: str
    result_validity: str
    reason: str


class PassAuthority:
    @staticmethod
    def decide(
        *,
        valid_target: bool,
        valid_contract: bool,
        executed: bool,
        assertions: Optional[List[AssertionResult]] = None,
        blocked: bool = False,
        infrastructure_failure: bool = False,
        unresolved_parameters: bool = False,
        target_reason: str = "",
        contract_reason: str = "",
    ) -> PassDecision:
        assertions = assertions or []
        assertions_executed = any(item.executed for item in assertions)
        assertions_passed = assertions_executed and all(item.passed for item in assertions if item.executed)

        if infrastructure_failure:
            return PassDecision(ExecutionStatus.INFRASTRUCTURE_FAILURE.value, ResultValidity.UNVERIFIED.value, target_reason or contract_reason or "Infrastructure failure")
        if blocked or unresolved_parameters:
            return PassDecision(ExecutionStatus.BLOCKED.value, ResultValidity.UNVERIFIED.value, contract_reason or target_reason or "Blocked")
        if not valid_target:
            return PassDecision(ExecutionStatus.INVALID_TARGET.value, ResultValidity.INVALID.value, target_reason or "Invalid target")
        if not valid_contract:
            return PassDecision(ExecutionStatus.INVALID_TEST.value, ResultValidity.INVALID.value, contract_reason or "Invalid test contract")
        if not executed:
            return PassDecision(ExecutionStatus.UNVERIFIED.value, ResultValidity.UNVERIFIED.value, "Test was not executed")
        if not assertions_executed:
            return PassDecision(ExecutionStatus.UNVERIFIED.value, ResultValidity.UNVERIFIED.value, "No assertion was executed")
        if assertions_passed:
            return PassDecision(ExecutionStatus.PASSED.value, ResultValidity.VALID.value, "All executed assertions passed with evidence")
        return PassDecision(ExecutionStatus.FAILED.value, ResultValidity.VALID.value, "One or more assertions failed")

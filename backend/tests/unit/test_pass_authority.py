"""Regression: PassAuthority must not allow false PASSED decisions."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.execution.pass_authority import PassAuthority, ExecutionStatus, ResultValidity
from app.core.execution.assertion_engine import AssertionResult


class TestPassAuthorityNoFalsePass:
    def test_no_assertions_no_pass(self):
        result = PassAuthority.decide(
            valid_target=True,
            valid_contract=True,
            executed=True,
            assertions=[],
        )
        assert result.status == ExecutionStatus.UNVERIFIED.value
        assert result.result_validity == ResultValidity.UNVERIFIED.value
        assert result.status != ExecutionStatus.PASSED.value

    def test_assertion_failed_never_pass(self):
        # Executed assertion that failed
        failed = AssertionResult(
            assertion_type="status_code",
            expected=200,
            actual=404,
            passed=False,
            executed=True,
            evidence="status_code=404, expected=200",
        )
        result = PassAuthority.decide(
            valid_target=True,
            valid_contract=True,
            executed=True,
            assertions=[failed],
        )

        assert result.status == ExecutionStatus.FAILED.value
        assert result.result_validity == ResultValidity.VALID.value
        assert result.status != ExecutionStatus.PASSED.value

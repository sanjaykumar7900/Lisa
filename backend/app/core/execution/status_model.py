"""Canonical LISA execution, runtime, and result states."""

from enum import Enum


class DependencyState(str, Enum):
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"


class RuntimeState(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    STARTING = "STARTING"
    READY = "READY"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class ExecutionStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"
    UNVERIFIED = "UNVERIFIED"
    INVALID_TEST = "INVALID_TEST"
    INVALID_TARGET = "INVALID_TARGET"
    INFRASTRUCTURE_FAILURE = "INFRASTRUCTURE_FAILURE"
    FLAKY = "FLAKY"


class ResultValidity(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    UNVERIFIED = "UNVERIFIED"


class HealthLayer(str, Enum):
    PROCESS_RUNNING = "PROCESS_RUNNING"
    PORT_LISTENING = "PORT_LISTENING"
    PROTOCOL_READY = "PROTOCOL_READY"
    APPLICATION_HEALTHY = "APPLICATION_HEALTHY"


class FailureClass(str, Enum):
    APPLICATION_BUG = "APPLICATION_BUG"
    TEST_BUG = "TEST_BUG"
    INVALID_TARGET = "INVALID_TARGET"
    INVALID_TEST = "INVALID_TEST"
    ENVIRONMENT_FAILURE = "ENVIRONMENT_FAILURE"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    TIMEOUT = "TIMEOUT"
    UNVERIFIED = "UNVERIFIED"
    LISA_BUG = "LISA_BUG"
    INFRASTRUCTURE_FAILURE = "INFRASTRUCTURE_FAILURE"


PASS_STATUSES = {ExecutionStatus.PASSED.value}
FAIL_STATUSES = {ExecutionStatus.FAILED.value}
EXCLUDED_FROM_PASS_RATE = {
    ExecutionStatus.BLOCKED.value,
    ExecutionStatus.INVALID_TEST.value,
    ExecutionStatus.INVALID_TARGET.value,
    ExecutionStatus.UNVERIFIED.value,
    ExecutionStatus.INFRASTRUCTURE_FAILURE.value,
    ExecutionStatus.SKIPPED.value,
    ExecutionStatus.FLAKY.value,
    ExecutionStatus.NOT_STARTED.value,
    ExecutionStatus.RUNNING.value,
}


class ExecutionRecord:
    def __init__(self, test_id: str):
        self.test_id = test_id
        self.status = ExecutionStatus.BLOCKED.value
        self.reason = ""
        self.dependency = None
        self.attempt_number = 1
        self.execution_id = None

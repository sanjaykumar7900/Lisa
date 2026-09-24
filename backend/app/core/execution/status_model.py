"""Patch item 5-7: BLOCKED ≠ FAILED, status model, truthful execution."""
class ExecutionRecord:
    def __init__(self, test_id: str):
        self.test_id = test_id
        self.status = "BLOCKED"  # PASSED / FAILED / BLOCKED / SKIPPED / ERROR / RUNNING
        self.reason = ""
        self.dependency = None

class ExecutionStatus:
    BLOCKED = "BLOCKED"
    PASS = "PASSED"
    FAIL = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"
    RUNNING = "RUNNING"

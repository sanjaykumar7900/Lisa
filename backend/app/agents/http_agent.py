"""Phase 1 — HTTP Agent with test oracle integration."""
from .core.oracle.api_oracle import APIOracle
from .core.memory.test_memory import TestMemory

class HTTPAgent:
    def __init__(self):
        self.oracle = APIOracle()
        self.memory = TestMemory()

    def execute(self, response, expected_status=200, required_fields=None):
        evidence = []
        evidence.append(self.oracle.assert_status(response, expected_status))
        if required_fields:
            evidence.append(self.oracle.assert_json_schema(response, required_fields))
        passed = all(e.passed for e in evidence)
        return {"passed": passed, "evidence": [e.model_dump() for e in evidence]}

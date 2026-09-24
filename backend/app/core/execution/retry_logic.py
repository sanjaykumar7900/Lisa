"""Item 13 — Retry logic (safe recovery, limited)."""
class RetryLogic:
    def attempt(self, max_attempts=2):
        for i in range(1, max_attempts+1):
            yield {"attempt": i, "status": "RETRYING"}

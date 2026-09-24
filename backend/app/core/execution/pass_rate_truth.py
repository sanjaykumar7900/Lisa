"""Item 9 — truthful pass-rate (blocked excluded, N/A if 0 executed)."""
class PassRateTruth:
    @staticmethod
    def compute(passed: int, failed: int, error: int, blocked: int) -> str:
        executed = passed + failed + error
        if executed == 0:
            return "N/A"
        return f"{passed/executed*100:.1f}%"

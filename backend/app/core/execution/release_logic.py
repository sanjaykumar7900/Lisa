"""Item 10 — Release recommendation (deterministic, only with evidence)."""
class ReleaseLogic:
    @staticmethod
    def recommend(executed: int, passed: int, critical_defects: int, blocked: bool) -> str:
        if blocked or executed == 0:
            return "NOT_ASSESSED"
        if executed > 0 and critical_defects > 0:
            return "FAIL"
        if executed > 0 and passed == executed:
            return "PASS"
        return "NOT_ASSESSED"

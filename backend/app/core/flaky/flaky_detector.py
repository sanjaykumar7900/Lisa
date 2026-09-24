"""Phase 6 — Flaky Test Detection."""
from pydantic import BaseModel
class FlakyResult(BaseModel):
    status: str = "FLAKY"
    flakiness_score: float = 0.4
    possible_causes: list = ["timing", "async loading"]

class FlakyDetector:
    def detect(self, results: list[bool]) -> FlakyResult:
        passes = sum(results)
        total = len(results)
        score = 1.0 - (passes / total) if total else 0
        return FlakyResult(status="FLAKY" if 0 < score < 1 else ("PASS" if score == 0 else "FAIL"), flakiness_score=round(score, 2))

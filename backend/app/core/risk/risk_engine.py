"""Phase 3 — Risk-Based Test Planning engine."""
from pydantic import BaseModel
from typing import Optional

class RiskScore(BaseModel):
    level: str = "LOW"  # CRITICAL / HIGH / MEDIUM / LOW
    priority: str = "P3"  # P0 / P1 / P2 / P3
    reasoning: str = ""

class RiskEngine:
    def calculate(self, endpoint: str, history_defects: int = 0, auth_required: bool = False) -> RiskScore:
        # Simple deterministic rule (per master: prefer deterministic over LLM)
        score = history_defects * 2 + (2 if auth_required else 0)
        if score >= 3: return RiskScore(level="CRITICAL", priority="P0", reasoning="high historical + auth")
        if score == 2: return RiskScore(level="HIGH", priority="P1", reasoning="auth or 1 prior defect")
        if score == 1: return RiskScore(level="MEDIUM", priority="P2", reasoning="low history")
        return RiskScore(level="LOW", priority="P3", reasoning="no history, no auth")

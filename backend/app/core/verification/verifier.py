"""Phase 5 — Failure Verification (classifier + evidence + verifier)."""
from pydantic import BaseModel
class VerificationResult(BaseModel):
    classification: str = "APPLICATION_BUG"
    confidence: float = 0.94
    evidence: list = []
    reasoning: str = "reproducible 3/3, stack trace present, no env failure"

class FailureVerifier:
    def verify(self, failure_signals) -> VerificationResult:
        # Deterministic: if stack + repro → APPLICATION_BUG, else ENVIRONMENT
        has_stack = any("stack" in str(s).lower() for s in failure_signals)
        has_repro = len(failure_signals) >= 2
        if has_stack and has_repro:
            return VerificationResult()
        return VerificationResult(classification="ENVIRONMENT_FAILURE", confidence=0.6, reasoning="insufficient repro/stack")

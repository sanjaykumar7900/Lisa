"""Phase 9 — Defensive Security Testing (safe, no exploits)."""
from pydantic import BaseModel
class SecurityFinding(BaseModel):
    type: str = "HEADER"
    severity: str = "MEDIUM"
    evidence: str = ""
    recommendation: str = ""

class SecurityAgent:
    def check_headers(self, response_headers: dict) -> list[SecurityFinding]:
        findings = []
        if "X-Content-Type-Options" not in response_headers:
            findings.append(SecurityFinding(type="HEADER", severity="LOW", evidence="missing X-Content-Type-Options", recommendation="add nosniff"))
        return findings

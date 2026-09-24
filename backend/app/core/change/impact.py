"""Phase 4 — Change Impact Analysis."""
from typing import List
class ChangeImpact:
    def affected_by(self, changed_file: str) -> List[str]:
        # Deterministic mapping (master: prefer deterministic)
        mapping = {
            "payment_service.py": ["POST /payment", "POST /checkout", "order confirmation"],
            "auth_service.py": ["POST /login", "GET /profile", "auth middleware"],
        }
        return mapping.get(changed_file, [])

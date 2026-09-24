"""Phase 2 — Test Memory (persistent results, defects, flaky history)."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TestMemoryRecord(BaseModel):
    run_id: str
    endpoint: Optional[str] = None
    result: str = "PASS"  # PASS / FAIL / FLAKY / REGENERATION
    defect_id: Optional[str] = None  # links to previous DEFECT
    flakiness_score: float = 0.0
    timestamp: datetime = datetime.now()

class TestMemory:
    def __init__(self):
        self.records: List[TestMemoryRecord] = []

    def add(self, r: TestMemoryRecord):
        self.records.append(r)

    def previous_defect_for(self, endpoint: str) -> Optional[TestMemoryRecord]:
        for rec in reversed(self.records):
            if rec.endpoint == endpoint and rec.defect_id:
                return rec
        return None

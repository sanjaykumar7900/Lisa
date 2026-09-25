"""Flaky detection from historical attempt statuses."""

from __future__ import annotations

from typing import Iterable, List

from pydantic import BaseModel, Field


class FlakyResult(BaseModel):
    status: str = "STABLE"
    flakiness_score: float = 0.0
    possible_causes: list = Field(default_factory=list)


class FlakyDetector:
    def detect(self, results: Iterable[bool] | Iterable[str]) -> FlakyResult:
        values: List[str] = []
        for item in results:
            if isinstance(item, bool):
                values.append("PASSED" if item else "FAILED")
            else:
                values.append(str(item).upper())
        if not values:
            return FlakyResult(status="UNKNOWN", flakiness_score=0.0)
        unique = set(values)
        if "PASSED" in unique and "FAILED" in unique:
            score = min(1.0, values.count("FAILED") / len(values) + 0.25)
            return FlakyResult(
                status="FLAKY",
                flakiness_score=round(score, 2),
                possible_causes=["non-deterministic application behavior", "timing", "shared test data"],
            )
        if unique == {"PASSED"}:
            return FlakyResult(status="PASSED", flakiness_score=0.0)
        return FlakyResult(status="FAILED", flakiness_score=1.0)

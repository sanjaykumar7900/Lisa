"""Release recommendation is evidence-gated and never based on invalid tests."""

from __future__ import annotations

from typing import Any, Dict, Iterable


class ReleaseLogic:
    @staticmethod
    def recommend(
        executed: int,
        passed: int,
        critical_defects: int = 0,
        blocked: bool = False,
        infrastructure_blocked: bool = False,
    ) -> str:
        if blocked or infrastructure_blocked or executed == 0:
            return "NOT_ASSESSED"
        if critical_defects > 0:
            return "FAIL"
        if executed > 0 and passed == executed:
            return "PASS"
        return "NOT_ASSESSED"

    @staticmethod
    def from_summary(summary: Dict[str, Any], bugs: Iterable[Dict[str, Any]] | None = None) -> str:
        bugs = list(bugs or [])
        critical = sum(
            1
            for bug in bugs
            if str(bug.get("severity") or "").lower() == "critical"
            and str(bug.get("classification") or "APPLICATION_BUG") == "APPLICATION_BUG"
        )
        infrastructure_blocked = (summary.get("infrastructure_failures") or 0) > 0 and (summary.get("executed") or 0) == 0
        blocked = (summary.get("blocked") or 0) > 0 and (summary.get("executed") or 0) == 0
        return ReleaseLogic.recommend(
            executed=int(summary.get("executed") or 0),
            passed=int(summary.get("passed") or 0),
            critical_defects=critical,
            blocked=blocked,
            infrastructure_blocked=infrastructure_blocked,
        )

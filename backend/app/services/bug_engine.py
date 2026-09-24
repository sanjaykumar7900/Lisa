import datetime
import logging
from typing import Any, Dict, List, Optional
from app.db.schemas import BugResponse
from app.services.failure_analyzer import FailureClassificationSchema

logger = logging.getLogger(__name__)

class BugEngine:
    """
    Bug Engine responsible for generating complete, structured Bug reports for confirmed defects.
    """

    @staticmethod
    def create_bug_report(
        bug_index: int,
        run_id: str,
        test_case: Dict[str, Any],
        actual_error: str,
        analysis: FailureClassificationSchema,
        evidence_paths: List[str]
    ) -> Dict[str, Any]:
        
        bug_id = f"BUG-{bug_index:03d}"
        title = f"[{test_case.get('module', 'App')}] Defect in '{test_case.get('title')}'"

        # Determine Severity based on priority/risk
        tc_priority = test_case.get("priority", "MEDIUM").upper()
        tc_risk = test_case.get("risk", "MEDIUM").upper()

        if tc_priority == "HIGH" and tc_risk == "HIGH":
            severity = "Critical"
            priority = "P0"
        elif tc_priority == "HIGH" or tc_risk == "HIGH":
            severity = "High"
            priority = "P1"
        elif tc_priority == "MEDIUM":
            severity = "Medium"
            priority = "P2"
        else:
            severity = "Low"
            priority = "P3"

        steps = [f"Step {s.get('step_number')}: {s.get('action')} on '{s.get('target')}'" for s in test_case.get("steps", [])]
        if not steps:
            steps = ["1. Navigate to target application URL", f"2. Execute test scenario '{test_case.get('title')}'"]

        return {
            "bug_id": bug_id,
            "run_id": run_id,
            "test_case_id": test_case.get("id"),
            "title": title,
            "severity": severity,
            "priority": priority,
            "environment": "Playwright Headless Chromium / Node environment",
            "preconditions": "\n".join(test_case.get("preconditions", ["Application reachable"])),
            "steps_to_reproduce": steps,
            "expected_result": test_case.get("expected_result", "Operation completes successfully without error."),
            "actual_result": f"Execution failed with error: {actual_error}",
            "reproducibility": "100% (1/1 run)",
            "evidence_paths": evidence_paths,
            "impact": f"Affects module '{test_case.get('module')}' functionality and user experience.",
            "root_cause": analysis.suggested_root_cause or analysis.reasoning,
            "regression_test": f"Add automated Playwright assertion for '{test_case.get('title')}'",
            "github_issue_status": "NOT_CREATED"
        }

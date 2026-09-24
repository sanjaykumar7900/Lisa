import datetime
import json
import logging
from typing import Any, Dict, List
from jinja2 import Template

logger = logging.getLogger(__name__)

HTML_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LISA QA Assurance Report — {{ project.name }}</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }
        .container { max-width: 1000px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h1, h2, h3 { color: #38bdf8; margin-top: 0; }
        .badge { display: inline-block; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 14px; }
        .badge-pass { background: #10b981; color: #fff; }
        .badge-cond { background: #f59e0b; color: #fff; }
        .badge-fail { background: #ef4444; color: #fff; }
        .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 24px 0; }
        .metric-card { background: #0f172a; padding: 16px; border-radius: 8px; text-align: center; border: 1px solid #334155; }
        .metric-val { font-size: 28px; font-weight: bold; color: #f8fafc; }
        .metric-lbl { font-size: 12px; color: #94a3b8; text-transform: uppercase; }
        table { width: 100%; border-collapse: collapse; margin-top: 16px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #334155; }
        th { background: #0f172a; color: #38bdf8; }
        .section { margin-bottom: 32px; border-bottom: 1px solid #334155; padding-bottom: 24px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>LISA — Autonomous QA Testing Report</h1>
        <p><strong>Project:</strong> {{ project.name }} ({{ project.repo_url }})</p>
        <p><strong>Run ID:</strong> {{ run.run_number }} | <strong>Date:</strong> {{ run.completed_at or 'In Progress' }}</p>

        <div class="section">
            <h2>Release Recommendation</h2>
            <span class="badge {{ 'badge-pass' if report.recommendation == 'PASS' else ('badge-cond' if report.recommendation == 'CONDITIONAL PASS' else 'badge-fail') }}">
                {{ report.recommendation }}
            </span>
            <p>{{ report.recommendation_reasoning }}</p>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-val">{{ run.total_tests }}</div>
                <div class="metric-lbl">Total Executed</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color:#10b981;">{{ run.passed_tests }}</div>
                <div class="metric-lbl">Passed</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color:#ef4444;">{{ run.failed_tests }}</div>
                <div class="metric-lbl">Failed</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color:#38bdf8;">{{ report.pass_rate }}%</div>
                <div class="metric-lbl">Pass Rate</div>
            </div>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <p>{{ report.executive_summary }}</p>
        </div>

        <div class="section">
            <h2>Confirmed Defects ({{ bugs|length }})</h2>
            {% if bugs %}
            <table>
                <thead>
                    <tr>
                        <th>Bug ID</th>
                        <th>Title</th>
                        <th>Severity</th>
                        <th>Priority</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for bug in bugs %}
                    <tr>
                        <td>{{ bug.bug_id }}</td>
                        <td>{{ bug.title }}</td>
                        <td>{{ bug.severity }}</td>
                        <td>{{ bug.priority }}</td>
                        <td>Confirmed Defect</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p style="color:#10b981;">No confirmed defects detected during execution.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

class ReportEngine:
    """
    QA Report Engine responsible for assembling executive summaries, release recommendations,
    and rendering structured JSON and standalone HTML test report artifacts.
    """

    @staticmethod
    def generate_report_data(
        project: Dict[str, Any],
        run: Dict[str, Any],
        results: List[Dict[str, Any]],
        bugs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        
        valid_results = [result for result in results if result.get("result_validity", "VALID") == "VALID"]
        invalid_results = [result for result in results if result.get("result_validity", "VALID") != "VALID"]
        statuses = [result.get("status") for result in valid_results]
        total = len(statuses)
        passed = statuses.count("PASSED")
        failed = statuses.count("FAILED")
        blocked = sum(status in {"BLOCKED", "SKIPPED", "ERROR"} for status in statuses)
        executed = passed + failed

        if executed == 0:
            pass_rate = None
            recommendation = "NOT_ASSESSED"
            recommendation_reasoning = "No automated tests were executed. Release readiness could not be assessed."
            exec_summary = (
                f"LISA planned {total} test case(s) against {project.get('name')}. "
                f"No test cases were executed. Release Recommendation: NOT ASSESSED."
            )
        else:
            pass_rate = round((passed / executed * 100), 1)
            if failed == 0 and blocked == 0:
                recommendation = "PASS"
                recommendation_reasoning = "All automated test cases passed cleanly with 0 defects detected."
            elif failed > 0 and any(b.get("severity") == "Critical" for b in bugs):
                recommendation = "FAIL"
                recommendation_reasoning = f"Release blocked due to {failed} failed test(s) including Critical severity defects."
            elif failed > 0:
                recommendation = "CONDITIONAL PASS"
                recommendation_reasoning = f"{failed} test case(s) failed. Non-critical bugs flagged for patch review."
            else:
                recommendation = "BLOCKED"
                recommendation_reasoning = f"Execution yielded {passed} passed test(s) and {blocked} blocked test(s)."

            exec_summary = (
                f"LISA executed {executed} of {total} test case(s) against {project.get('name')}. "
                f"Pass rate reached {pass_rate}%. {len(bugs)} defect(s) were analyzed and logged."
            )

        report_data = {
            "executive_summary": exec_summary,
            "pass_rate": pass_rate,
            "recommendation": recommendation,
            "recommendation_reasoning": recommendation_reasoning,
            "test_coverage": "Measured from executed test cases; scenario coverage depends on the generated plan.",
            "automation_coverage": "Measured from test cases marked automation_candidate.",
            "blocked_tests": blocked,
            "execution_summary": {"total": len(results), "executed": executed, "passed": passed, "failed": failed, "blocked": blocked, "invalid": len(invalid_results), "pass_rate": pass_rate},
            "execution_quality": {"valid_executions": len(valid_results), "invalid_targets": sum(r.get("result_validity") == "INVALID_TARGET" for r in invalid_results), "unverified_assertions": sum(r.get("result_validity") == "UNVERIFIED" for r in invalid_results), "generated_test_defects": sum(r.get("result_validity") == "INVALID_TEST" for r in invalid_results)},
            "repository_information": {"name": project.get("name"), "repo_url": project.get("repo_url")},
            "detected_technology_stack": project.get("tech_stack", {}),
            "architecture": project.get("tech_stack", {}).get("architecture", []),
            "discovered_modules": project.get("modules", []),
            "test_strategy": "Derived from detected frontend, API, persistence, and repository modules.",
            "code_coverage": "NOT MEASURED",
            "recommendations": ["Review every failed test with its captured evidence.", "Add regression coverage for confirmed defects."],
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        # Render HTML from the same canonical execution-result totals.
        report_run = {**run, "total_tests": total, "passed_tests": passed, "failed_tests": failed}
        template = Template(HTML_REPORT_TEMPLATE)
        html_content = template.render(project=project, run=report_run, results=results, bugs=bugs, report=report_data)
        report_data["html_report"] = html_content

        return report_data

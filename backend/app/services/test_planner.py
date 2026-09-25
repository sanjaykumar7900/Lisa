import json
import logging
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from app.services.llm.factory import get_llm_provider
from app.db.schemas import TestCaseCreate, TestStep

logger = logging.getLogger(__name__)

class TestPlanSchema(BaseModel):
    modules: List[str] = Field(description="Discovered or prioritized project modules")
    risks: List[Dict[str, Any]] = Field(description="Identified risk areas with component, risk_level, description")
    test_scenarios: List[Dict[str, Any]] = Field(description="List of key test scenarios with id, title, module")
    priority: str = Field(default="HIGH", description="Overall priority for testing phase")

class GeneratedCasesSchema(BaseModel):
    cases: List[TestCaseCreate] = Field(description="Structured test cases ready for automation execution")

class TestPlanner:
    """
    AI Test Planner responsible for generating structured test plans and executable test cases
    based on repository stack analysis and application modules.
    """

    def __init__(self, repo_analysis: Dict[str, Any]):
        self.analysis = repo_analysis
        self.llm = get_llm_provider()

    def _repository_api_cases(self) -> List[Dict[str, Any]]:
        """Return only endpoint evidence extracted from the repository."""
        cases = []
        for index, endpoint in enumerate(self.analysis.get("api_endpoints", []), start=1):
            method = endpoint["method"].lower()
            action = f"http_{method}" if method in {"get", "post", "put", "delete", "patch"} else None
            if not action:
                continue

            raw_status = endpoint.get("expected_status")
            expected_status = raw_status if isinstance(raw_status, int) else None

            if expected_status is not None:
                step_expected = f"HTTP status is exactly {expected_status}"
                case_expected = f"The {method.upper()} {endpoint['path']} endpoint responds with status {expected_status} as documented."
                description = f"Verify the repository endpoint {method.upper()} {endpoint['path']} responds with status {expected_status} as documented by repository evidence."
                step: Dict[str, Any] = {
                    "step_number": 1,
                    "action": action,
                    "target": endpoint["path"],
                    "expected": step_expected,
                    "expected_status": expected_status,
                    "assertions": [{"type": "status_code", "expected": expected_status}],
                }
            else:
                step_expected = "No evidence-backed expected status discovered (unverified status assertion)"
                case_expected = f"The {method.upper()} {endpoint['path']} endpoint responds, but lacks an evidence-backed expected status assertion."
                description = f"Verify the repository endpoint {method.upper()} {endpoint['path']}; expected status is unverified without repository evidence."
                step = {
                    "step_number": 1,
                    "action": action,
                    "target": endpoint["path"],
                    "expected": step_expected,
                    "expected_status": None,
                }

            cases.append({
                "title": f"{method.upper()} {endpoint['path']} responds correctly",
                "description": description,
                "module": "REST API",
                "test_type": "api",
                "priority": "HIGH",
                "risk": "HIGH",
                "steps": [step],
                "expected": case_expected,
                "expected_status": expected_status,
                "evidence_source": endpoint.get("evidence", []),
            })
        return cases

    async def generate_test_plan(self) -> TestPlanSchema:
        prompt = (
            f"Analyze the following repository tech stack and generate a structured QA Test Plan.\n"
            f"Tech Stack: {json.dumps(self.analysis.get('languages', []))} | Frontend: {self.analysis.get('frontend')} | Backend: {self.analysis.get('backend')}\n"
            f"Modules Discovered: {json.dumps(self.analysis.get('modules', []))}\n"
            f"README Context:\n{self.analysis.get('readme_snippet', '')[:1000]}\n"
        )
        system_prompt = (
            "You are LISA, an expert AI QA Test Planner. Generate high-value, comprehensive test plans covering "
            "functional UI flows, negative tests, boundary conditions, and API endpoints."
        )

        try:
            return await self.llm.generate_structured(prompt, TestPlanSchema, system_prompt=system_prompt)
        except Exception as e:
            logger.warning(f"Error generating LLM test plan: {e}. Utilizing fallback plan.")
            fallback_llm = get_llm_provider(force_fallback=True)
            return await fallback_llm.generate_structured(prompt, TestPlanSchema)

    async def generate_test_cases(self, plan: TestPlanSchema) -> List[TestCaseCreate]:
        # Repository endpoint evidence is authoritative. Do not let an LLM replace
        # discovered paths or methods with generic framework examples.
        if self.analysis.get("api_endpoints"):
            return self._build_repository_cases(plan)
        if not self.llm.__class__.__name__ == "NvidiaProvider":
            return self._build_repository_cases(plan)
        prompt = (
            f"Based on the following Test Plan, generate structured executable test cases.\n"
            f"Modules: {json.dumps(plan.modules)}\n"
            f"Scenarios: {json.dumps(plan.test_scenarios)}\n\n"
            f"Provide at least 3-5 executable UI and API test cases with step-by-step actions.\n"
            f"Supported Browser Actions: open_url, click, type_text, select_option, press_key, get_page_text, get_page_title, take_screenshot, http_get, http_post.\n"
        )
        system_prompt = (
            "You are LISA Test Case Engine. Generate executable test cases with precise step-by-step target selectors "
            "or actions that Playwright and HTTP tools can execute."
        )

        try:
            result = await self.llm.generate_structured(prompt, GeneratedCasesSchema, system_prompt=system_prompt)
            return result.cases
        except Exception as e:
            logger.warning(f"Error generating LLM test cases: {e}. Utilizing fallback test cases.")
            fallback_llm = get_llm_provider(force_fallback=True)
            result = await fallback_llm.generate_structured(prompt, GeneratedCasesSchema)
            return result.cases

    def _build_repository_cases(self, plan: TestPlanSchema) -> List[TestCaseCreate]:
        """Build executable cases from detected capabilities instead of placeholder data."""
        cases: List[TestCaseCreate] = []
        counters = {"UI": 0, "API": 0, "INT": 0, "NEG": 0}

        def add(title: str, description: str, module: str, test_type: str, priority: str, risk: str, steps: List[Dict[str, Any]], expected: str, data: Dict[str, Any] | None = None):
            category = {"ui": "UI", "api": "API", "integration": "INT", "negative": "NEG"}.get(test_type, "QA")
            counters[category] = counters.get(category, 0) + 1
            cases.append(TestCaseCreate(
                test_id=f"TC-{category}-{counters[category]:03d}", title=title, description=description, module=module,
                priority=priority, risk=risk, preconditions=["Application is available at the detected URL"],
                test_data=data or {}, steps=[TestStep(**step) for step in steps], expected_result=expected,
                automation_candidate=True, test_type=test_type
            ))

        if self.analysis.get("frontend") and self.analysis.get("frontend") != "Not detected":
            add("Frontend application loads", "Verify the detected frontend renders without a client error.", "Frontend", "ui", "HIGH", "HIGH", [{"step_number": 1, "action": "open_url", "target": "/", "expected": "The application loads"}, {"step_number": 2, "action": "get_page_title", "target": "", "expected": "The page has a title"}], "The frontend loads and exposes its primary content.")
            add("Empty input is handled", "Check that empty user input does not create an invalid request.", "Frontend validation", "negative", "HIGH", "MEDIUM", [{"step_number": 1, "action": "open_url", "target": "/", "expected": "The application loads"}], "The application shows validation feedback and does not submit malformed data.")
        for endpoint_case in self._repository_api_cases():
            first_step = endpoint_case["steps"][0]
            expected_status = endpoint_case.get("expected_status")
            endpoint_id = f"{first_step['action']}:{first_step['target']}"
            case_data: Dict[str, Any] = {
                "endpoint_id": endpoint_id,
                "evidence_sources": endpoint_case["evidence_source"],
                "generated_from_evidence": True,
                "expected_status": expected_status,
            }
            if expected_status is not None:
                case_data["assertions"] = [{"type": "status_code", "expected": expected_status}]
            add(
                endpoint_case["title"],
                endpoint_case["description"],
                endpoint_case["module"],
                endpoint_case["test_type"],
                endpoint_case["priority"],
                endpoint_case["risk"],
                endpoint_case["steps"],
                endpoint_case["expected"],
                case_data,
            )
        if self.analysis.get("orm") != "Not detected" and self.analysis.get("database") != "Not detected":
            add("Persistence configuration is usable", "Verify application startup can initialize the detected persistence layer.", "Persistence", "integration", "MEDIUM", "MEDIUM", [{"step_number": 1, "action": "open_url", "target": "/", "expected": "Application is reachable"}], "The application starts with its configured database integration.")
        return cases

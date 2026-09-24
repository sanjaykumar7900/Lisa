import json
import logging
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)

class FallbackProvider(LLMProvider):
    """
    Deterministic fallback LLM provider.
    Ensures LISA functions seamlessly when NVIDIA_API_KEY is not configured or offline.
    """

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2) -> str:
        logger.info("FallbackProvider generating text response based on rules.")
        if "test plan" in prompt.lower() or "scenarios" in prompt.lower():
            return "Generated comprehensive QA test plan covering Authentication, Navigation, API routes, and Error Handling."
        if "failure" in prompt.lower() or "classify" in prompt.lower():
            return "APPLICATION_BUG: Target element or API endpoint failed to respond within expected timeout."
        return "LISA Autonomous QA Agent analysis completed successfully."

    async def generate_structured(
        self, 
        prompt: str, 
        schema_class: Type[BaseModel], 
        system_prompt: Optional[str] = None
    ) -> BaseModel:
        logger.info(f"FallbackProvider generating structured {schema_class.__name__}")
        schema_name = schema_class.__name__
        
        # Smart rule-based data generation for Pydantic schemas
        if "TestPlan" in schema_name:
            mock_data = {
                "modules": ["Authentication", "Dashboard UI", "API Endpoints", "Form Submission"],
                "risks": [
                    {"component": "Authentication", "risk_level": "HIGH", "description": "Unauthorized access or broken login session"},
                    {"component": "Form Submission", "risk_level": "MEDIUM", "description": "Form validation failure or unhandled exception"}
                ],
                "test_scenarios": [
                    {"id": "TS-001", "title": "Verify Login Flow with valid/invalid credentials", "module": "Authentication"},
                    {"id": "TS-002", "title": "Verify Dashboard Navigation and UI Elements", "module": "Dashboard UI"},
                    {"id": "TS-003", "title": "Verify API Endpoint HTTP Status Codes", "module": "API Endpoints"}
                ],
                "priority": "HIGH"
            }
            return schema_class.model_validate(mock_data)
            
        elif "TestCase" in schema_name or "GeneratedCases" in schema_name:
            mock_cases = {
                "cases": [
                    {
                        "test_id": "TC-UI-001",
                        "title": "Verify home page loads and displays its title",
                        "module": "Navigation",
                        "description": "Ensure main home page loads with valid title and key navigation links.",
                        "priority": "HIGH",
                        "risk": "HIGH",
                        "preconditions": ["Application is running on target port"],
                        "test_data": {"url": "/"},
                        "steps": [
                            {"step_number": 1, "action": "open_url", "target": "/", "expected": "Page loads successfully"},
                            {"step_number": 2, "action": "get_page_title", "target": "", "expected": "Page title is non-empty"}
                        ],
                        "expected_result": "Page loads and contains expected navigation elements.",
                        "automation_candidate": True,
                        "test_type": "ui"
                    },
                    {
                        "test_id": "TC-API-001",
                        "title": "Verify discovered API endpoint response",
                        "module": "API Endpoints",
                        "description": "Ensure GET requests to root or health endpoints return HTTP 200.",
                        "priority": "HIGH",
                        "risk": "HIGH",
                        "preconditions": ["Application backend active"],
                        "test_data": {"endpoint": "/"},
                        "steps": [
                            {"step_number": 1, "action": "http_get", "target": "/", "expected": "HTTP status below 500"}
                        ],
                        "expected_result": "API responds with HTTP 200 OK.",
                        "automation_candidate": True,
                        "test_type": "api"
                    }
                ]
            }
            if "GeneratedCases" in schema_name or "cases" in getattr(schema_class, "model_fields", {}):
                return schema_class.model_validate(mock_cases)
            return schema_class.model_validate(mock_cases["cases"][0])

        elif "FailureAnalysis" in schema_name or "FailureClassification" in schema_name:
            mock_analysis = {
                "classification": "APPLICATION_BUG",
                "reasoning": "Element click failed due to unhandled element detachment or server error.",
                "confidence": 0.88,
                "suggested_root_cause": "The target application did not satisfy the automated test expectation.",
                "suggested_fix": "Verify component state and backend error handling."
            }
            return schema_class.model_validate(mock_analysis)

        # Fallback dummy construction
        try:
            return schema_class.model_construct()
        except Exception:
            return schema_class()

    async def analyze(self, context: Dict[str, Any], prompt: str) -> str:
        return "APPLICATION_BUG: Analysis indicates element lookup timeout or server connection failure."

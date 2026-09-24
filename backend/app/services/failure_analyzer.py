import asyncio
import json
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.services.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)

class FailureClassificationSchema(BaseModel):
    classification: str = Field(
        description="Failure category: APPLICATION_BUG, TEST_BUG, ENVIRONMENT_FAILURE, NETWORK_FAILURE, DEPENDENCY_FAILURE, UNKNOWN"
    )
    reasoning: str = Field(description="Detailed technical reasoning for classification based on evidence")
    confidence: float = Field(default=0.9, description="Confidence score between 0.0 and 1.0")
    suggested_root_cause: str = Field(description="Likely root cause analysis")
    suggested_fix: str = Field(description="Recommended bug fix or mitigation step")

class FailureAnalyzer:
    """
    AI Failure & Bug Classifier for LISA.
    Analyzes failed test case execution data, step traces, console logs, network requests,
    and screenshots to categorize the failure and produce actionable root cause diagnosis.
    """

    def __init__(self):
        self.llm = get_llm_provider()

    async def analyze_failure(self, failure_context: Dict[str, Any]) -> FailureClassificationSchema:
        prompt = (
            "Analyze the following failed test execution evidence and classify the root cause failure.\n"
            f"Test Case: {failure_context.get('test_case_id')} - {failure_context.get('title')}\n"
            f"Step Failed: {json.dumps(failure_context.get('failed_step', {}))}\n"
            f"Expected Result: {failure_context.get('expected_result')}\n"
            f"Actual Error: {failure_context.get('error_message')}\n"
            f"Console Logs: {json.dumps(failure_context.get('console_logs', [])[:10])}\n"
            f"Network Requests: {json.dumps(failure_context.get('network_requests', [])[:10])}\n"
        )
        system_prompt = (
            "You are LISA Failure Analyzer. Classify failure into one of: "
            "APPLICATION_BUG, TEST_BUG, ENVIRONMENT_FAILURE, NETWORK_FAILURE, DEPENDENCY_FAILURE, UNKNOWN. "
            "Only classify as APPLICATION_BUG if evidence shows application code failed or returned error response."
        )

        try:
            return await asyncio.wait_for(
                self.llm.generate_structured(prompt, FailureClassificationSchema, system_prompt=system_prompt),
                timeout=15,
            )
        except Exception as e:
            logger.warning(f"LLM failure analysis failed ({e}). Using Fallback classification.")
            fallback_llm = get_llm_provider(force_fallback=True)
            return await fallback_llm.generate_structured(prompt, FailureClassificationSchema)

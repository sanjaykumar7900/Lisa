import pytest
from app.services.llm.factory import get_llm_provider
from app.services.llm.fallback_provider import FallbackProvider
from app.services.report_engine import ReportEngine

@pytest.mark.asyncio
async def test_fallback_llm_provider():
    llm = get_llm_provider(force_fallback=True)
    assert isinstance(llm, FallbackProvider)
    
    resp = await llm.generate("Generate QA test plan for app")
    assert "test plan" in resp.lower() or "lisa" in resp.lower()

def test_report_engine_generation():
    proj = {"name": "Test Project", "repo_url": "https://github.com/example/test"}
    run = {"run_number": "RUN-001", "total_tests": 5, "passed_tests": 5, "failed_tests": 0}
    results = [
        {"status": "PASSED"},
        {"status": "PASSED"},
        {"status": "FAILED"},
    ]
    bugs = []
    
    report = ReportEngine.generate_report_data(proj, run, results, bugs)
    assert report["recommendation"] == "CONDITIONAL PASS"
    assert report["pass_rate"] == 66.7
    assert "html_report" in report


def test_empty_execution_results_are_blocked():
    report = ReportEngine.generate_report_data(
        {"name": "Empty Project", "repo_url": "https://github.com/example/empty"},
        {"run_number": "RUN-EMPTY", "total_tests": 10, "passed_tests": 10, "failed_tests": 0},
        [],
        [],
    )
    assert report["recommendation"] == "NOT_ASSESSED"
    assert report["pass_rate"] is None

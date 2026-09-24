import csv
import io
import logging
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select

from app.db.database import get_db
from app.db.models import AgentAction, Project, TestPlan, TestCase, TestRun, TestExecutionResult, Bug, Evidence
from app.db.schemas import (
    ProjectCreate, ProjectResponse, TestPlanResponse, TestCaseResponse,
    TestRunCreate, TestRunResponse, BugResponse, EvidenceResponse
)
from app.services.orchestrator import QAOrchestrator
from app.services.report_engine import ReportEngine
from app.websocket.log_streamer import ws_manager
from app.core.security import normalize_repo_url, validate_repo_url
from app.middleware.auth import require_api_key

router = APIRouter()
logger = logging.getLogger(__name__)


async def _execution_counts(run_id: str, db: AsyncSession) -> dict[str, int]:
    result = await db.execute(select(TestExecutionResult.status).where(TestExecutionResult.run_id == run_id))
    statuses = [status for (status,) in result.all()]
    return {
        "total_tests": len(statuses),
        "passed_tests": statuses.count("PASSED"),
        "failed_tests": statuses.count("FAILED"),
        "blocked_tests": sum(status in {"BLOCKED", "SKIPPED", "ERROR"} for status in statuses),
    }


async def _run_response(run: TestRun, db: AsyncSession) -> TestRunResponse:
    counts = await _execution_counts(run.id, db)
    return TestRunResponse.model_validate({**run.__dict__, **counts})

@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    _auth: Optional[str] = Depends(require_api_key),
):
    repo_url = normalize_repo_url(payload.repo_url)
    is_valid, msg = validate_repo_url(repo_url)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    # Derive project name if not specified
    name = payload.name
    if not name:
        name = repo_url.rstrip("/").split("/")[-1].replace(".git", "").capitalize()

    # Check existing
    res = await db.execute(select(Project).where(Project.repo_url == repo_url))
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    project = Project(
        name=name,
        repo_url=repo_url,
        startup_command=payload.startup_command,
        app_port=payload.app_port,
        status="CREATED"
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    res = await db.execute(select(Project).order_by(Project.created_at.desc()).offset(skip).limit(limit))
    return list(res.scalars().all())

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Project).where(Project.id == project_id))
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: Optional[str] = Depends(require_api_key),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    run_ids = select(TestRun.id).where(TestRun.project_id == project_id)
    test_case_ids = select(TestCase.id).where(TestCase.project_id == project_id)
    await db.execute(delete(AgentAction).where(AgentAction.run_id.in_(run_ids)))
    await db.execute(delete(Evidence).where(Evidence.run_id.in_(run_ids)))
    await db.execute(delete(Bug).where(Bug.run_id.in_(run_ids)))
    await db.execute(delete(TestExecutionResult).where(TestExecutionResult.run_id.in_(run_ids)))
    await db.execute(delete(TestExecutionResult).where(TestExecutionResult.test_case_id.in_(test_case_ids)))
    await db.execute(delete(TestRun).where(TestRun.project_id == project_id))
    await db.execute(delete(TestCase).where(TestCase.project_id == project_id))
    await db.execute(delete(TestPlan).where(TestPlan.project_id == project_id))
    await db.execute(delete(Project).where(Project.id == project_id))
    await db.commit()
    clone_path = Path(project.local_path) if project.local_path else None
    if clone_path and clone_path.exists():
        shutil.rmtree(clone_path, ignore_errors=True)
    return {"message": "Project deleted", "project_id": project_id}

@router.post("/projects/{project_id}/analyze", response_model=ProjectResponse)
async def analyze_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: Optional[str] = Depends(require_api_key),
):
    orchestrator = QAOrchestrator(db)
    try:
        return await orchestrator.analyze_project(project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/projects/{project_id}/test-plan", response_model=TestPlanResponse)
async def generate_test_plan(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: Optional[str] = Depends(require_api_key),
):
    orchestrator = QAOrchestrator(db)
    try:
        plan = await orchestrator.generate_test_plan(project_id)
        # Fetch populated test cases
        tc_res = await db.execute(select(TestCase).where(TestCase.plan_id == plan.id))
        test_cases = list(tc_res.scalars().all())
        return TestPlanResponse(
            id=plan.id,
            project_id=plan.project_id,
            modules=plan.modules,
            risks=plan.risks,
            test_scenarios=plan.test_scenarios,
            priority=plan.priority,
            created_at=plan.created_at,
            test_cases=test_cases,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/projects/{project_id}/test", response_model=TestRunResponse)
async def start_test_run(
    project_id: str,
    payload: TestRunCreate,
    db: AsyncSession = Depends(get_db),
    _auth: Optional[str] = Depends(require_api_key),
):
    orchestrator = QAOrchestrator(db)
    try:
        # Pass user-selected dropdown options to orchestrator (test_types, scopes, etc.)
        test_options = payload.test_options if hasattr(payload, 'test_options') else None
        run = await orchestrator.execute_test_run(
            project_id,
            autonomy_level=payload.autonomy_level,
            test_options=test_options
        )
        return await _run_response(run, db)
    except Exception as e:
        logger.exception("Failed to start test run for project %s", project_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-runs", response_model=List[TestRunResponse])
async def list_test_runs(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    res = await db.execute(select(TestRun).order_by(TestRun.started_at.desc()).offset(skip).limit(limit))
    return [await _run_response(run, db) for run in res.scalars().all()]

@router.get("/test-runs/{run_id}", response_model=TestRunResponse)
async def get_test_run(run_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TestRun).where(TestRun.id == run_id))
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")
    return await _run_response(run, db)

@router.get("/bugs", response_model=List[BugResponse])
async def list_bugs(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    res = await db.execute(select(Bug).order_by(Bug.created_at.desc()).offset(skip).limit(limit))
    return list(res.scalars().all())

@router.get("/bugs/{bug_id}", response_model=BugResponse)
async def get_bug(bug_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Bug).where(Bug.id == bug_id))
    bug = res.scalar_one_or_none()
    if not bug:
        raise HTTPException(status_code=404, detail="Bug not found")
    return bug

@router.post("/bugs/{bug_id}/approve-issue")
async def approve_github_issue(
    bug_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: Optional[str] = Depends(require_api_key),
):
    """Human approval endpoint for GitHub Issue creation."""
    res = await db.execute(select(Bug).where(Bug.id == bug_id))
    bug = res.scalar_one_or_none()
    if not bug:
        raise HTTPException(status_code=404, detail="Bug not found")
    
    bug.github_issue_status = "CREATED"
    bug.github_issue_url = f"https://github.com/mock-repo/issues/{bug.bug_id.lower()}"
    await db.commit()
    return {"message": "GitHub issue approved and created", "github_issue_url": bug.github_issue_url}

@router.get("/reports/{run_id}")
async def get_qa_report(run_id: str, db: AsyncSession = Depends(get_db)):
    res_run = await db.execute(select(TestRun).where(TestRun.id == run_id))
    run = res_run.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")

    res_proj = await db.execute(select(Project).where(Project.id == run.project_id))
    proj = res_proj.scalar_one_or_none()

    res_results = await db.execute(select(TestExecutionResult).where(TestExecutionResult.run_id == run_id))
    results = [r.__dict__ for r in res_results.scalars().all()]

    res_bugs = await db.execute(select(Bug).where(Bug.run_id == run_id))
    bugs = [b.__dict__ for b in res_bugs.scalars().all()]

    report = ReportEngine.generate_report_data(
        project=proj.__dict__ if proj else {},
        run=run.__dict__,
        results=results,
        bugs=bugs
    )
    return report


@router.get("/test-runs/{run_id}/results.csv")
async def download_test_results(run_id: str, db: AsyncSession = Depends(get_db)):
    run_result = await db.execute(select(TestRun).where(TestRun.id == run_id))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")

    result_rows = await db.execute(
        select(TestExecutionResult, TestCase)
        .join(TestCase, TestCase.id == TestExecutionResult.test_case_id)
        .where(TestExecutionResult.run_id == run_id)
        .order_by(TestExecutionResult.executed_at.asc())
    )

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "run_number", "test_id", "title", "module", "test_type", "status", "result_validity", "attempt_number", "endpoint_id", "evidence_sources", "generated_from_evidence",
        "duration_seconds", "expected_result", "actual_result", "error_message", "stdout", "stderr", "executed_at",
    ])
    for result, test_case in result_rows.all():
        writer.writerow([
            run.run_number,
            test_case.test_id,
            test_case.title,
            test_case.module,
            test_case.test_type,
            result.status,
            result.result_validity,
            result.attempt_number,
            (test_case.test_data or {}).get("endpoint_id", ""),
            ";".join((test_case.test_data or {}).get("evidence_sources", [])),
            (test_case.test_data or {}).get("generated_from_evidence", False),
            result.duration,
            test_case.expected_result,
            result.actual_result or "",
            result.error_message or "",
            result.stdout or "",
            result.stderr or "",
            result.executed_at.isoformat() if result.executed_at else "",
        ])

    filename = f"{run.run_number.lower()}-test-results.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.websocket("/ws/runs/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await ws_manager.connect(run_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, websocket)

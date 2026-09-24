import asyncio
import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import validate_startup_command
from app.db.models import Project, TestPlan, TestCase, TestRun, TestExecutionResult, Bug, Evidence, AgentAction
from app.services.repo_agent import RepositoryAgent
from app.services.test_planner import TestPlanner
from app.services.app_runner import ApplicationRunner
from app.services.browser_agent import BrowserAgent
from app.services.api_tester import APITester
from app.services.failure_analyzer import FailureAnalyzer
from app.services.bug_engine import BugEngine
from app.services.report_engine import ReportEngine
from app.core.execution.runtime_context import RuntimeContext
from app.websocket.log_streamer import ws_manager

logger = logging.getLogger(__name__)

class QAOrchestrator:
    """
    Main Orchestrator engine for LISA.
    Coordinates Repository Analysis, Test Generation, Application Startup,
    Browser/API Execution, Failure Analysis, Defect Generation, and Reporting.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _emit_log(self, run_id: str, message: str, status: str = "info", data: Optional[Dict] = None):
        payload = {
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "run_id": run_id,
            "message": message,
            "status": status,
            "data": data or {}
        }
        logger.info(f"Orchestrator [{run_id}]: {message}")
        await ws_manager.broadcast(run_id, payload)

    async def analyze_project(self, project_id: str) -> Project:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        project.status = "ANALYZING"
        await self.db.commit()

        agent = RepositoryAgent(repo_url=project.repo_url, project_id=project.id)
        tech_analysis = agent.analyze()

        project.local_path = str(agent.clone_path)
        project.tech_stack = tech_analysis
        project.modules = tech_analysis.get("modules", [])
        if tech_analysis.get("startup_commands"):
            commands = [c for c in tech_analysis["startup_commands"] if validate_startup_command(c)[0]]
            if commands:
                project.startup_command = next((command for command in commands if "spring-boot" in command or command.startswith("mvn ") or command.startswith("gradle ")), commands[0])
            else:
                project.startup_command = None
        else:
            project.startup_command = None

        service_ports = tech_analysis.get("ports", [])
        backend_port = next((item["port"] for item in service_ports if item.get("name") == "Backend"), None)
        frontend_port = next((item["port"] for item in service_ports if item.get("name") == "Frontend"), None)
        project.app_port = backend_port or frontend_port
        project.status = "ANALYZED"
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def generate_test_plan(self, project_id: str) -> TestPlan:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        planner = TestPlanner(repo_analysis=project.tech_stack or {})
        plan_data = await planner.generate_test_plan()

        db_plan = TestPlan(
            project_id=project.id,
            modules=plan_data.modules,
            risks=plan_data.risks,
            test_scenarios=plan_data.test_scenarios,
            priority=plan_data.priority
        )
        self.db.add(db_plan)
        await self.db.commit()
        await self.db.refresh(db_plan)

        # Generate TestCase records
        raw_cases = await planner.generate_test_cases(plan_data)
        for tc in raw_cases:
            db_case = TestCase(
                project_id=project.id,
                plan_id=db_plan.id,
                test_id=tc.test_id,
                title=tc.title,
                module=tc.module,
                description=tc.description,
                priority=tc.priority,
                risk=tc.risk,
                preconditions=tc.preconditions,
                test_data=tc.test_data,
                steps=[s.model_dump() for s in tc.steps],
                expected_result=tc.expected_result,
                automation_candidate=tc.automation_candidate,
                test_type=tc.test_type
            )
            self.db.add(db_case)

        await self.db.commit()
        return db_plan

    async def execute_test_run(self, project_id: str, autonomy_level: int = 3, test_options: Optional[Dict[str, Any]] = None) -> TestRun:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        if project.local_path and not (project.tech_stack or {}).get("api_endpoints"):
            agent = RepositoryAgent(repo_url=project.repo_url, project_id=project.id)
            agent.clone_path = Path(project.local_path)
            refreshed_analysis = agent.analyze()
            project.tech_stack = refreshed_analysis
            project.modules = refreshed_analysis.get("modules", [])
            project.startup_command = refreshed_analysis.get("startup_command")
            await self.db.commit()

        # Rebuild cases from the latest repository analysis so stale generic cases
        # cannot leak into a new run.
        tc_result = await self.db.execute(select(TestCase).where(TestCase.project_id == project_id))
        test_cases = list(tc_result.scalars().all())

        if not test_cases:
            fresh_plan = await self.generate_test_plan(project_id)
            tc_result = await self.db.execute(select(TestCase).where(TestCase.plan_id == fresh_plan.id))
            test_cases = list(tc_result.scalars().all())
        elif project.tech_stack and project.tech_stack.get("api_endpoints"):
            fresh_plan = await self.generate_test_plan(project_id)
            tc_result = await self.db.execute(select(TestCase).where(TestCase.plan_id == fresh_plan.id))
            test_cases = list(tc_result.scalars().all())

        # Count runs for number
        run_count_res = await self.db.execute(select(TestRun).where(TestRun.project_id == project_id))
        run_count = len(list(run_count_res.scalars().all())) + 1
        run_number = f"RUN-{run_count:03d}"

        test_run = TestRun(
            project_id=project.id,
            run_number=run_number,
            autonomy_level=autonomy_level,
            status="RUNNING",
            started_at=datetime.datetime.now(datetime.timezone.utc),
            total_tests=0
        )
        self.db.add(test_run)
        await self.db.commit()
        await self.db.refresh(test_run)

        # Apply user-selected dropdown test options (filter test cases)
        if test_options:
            allowed_types = test_options.get("test_types")
            allowed_scopes = test_options.get("scopes")
            if allowed_types:
                test_cases = [tc for tc in test_cases if tc.test_type in allowed_types]
            if allowed_scopes:
                scopes = [allowed_scopes] if isinstance(allowed_scopes, str) else allowed_scopes
                normalized_scopes = {str(scope).strip().lower() for scope in scopes}
                if "all modules" not in normalized_scopes:
                    def matches_scope(test_case: TestCase) -> bool:
                        module = (test_case.module or "").lower()
                        if "frontend only" in normalized_scopes:
                            return "front" in module or test_case.test_type == "ui"
                        if "backend only" in normalized_scopes:
                            return any(token in module for token in ("back", "api", "rest", "server")) or test_case.test_type == "api"
                        if "api only" in normalized_scopes:
                            return test_case.test_type == "api" or "api" in module
                        return module in normalized_scopes
                    test_cases = [tc for tc in test_cases if matches_scope(tc)]
            await self._emit_log(test_run.id, f"Test options applied: {test_options}. Running {len(test_cases)} test cases.", status="info")

        if not test_cases:
            raise ValueError("No executable test cases matched the selected test options. Select All Modules or generate a test plan first.")

        # Launch async execution pipeline
        task = asyncio.create_task(self._run_pipeline(project, test_run, test_cases))
        # Keep a reference so we can await/cancel it on shutdown if needed.
        test_run._pipeline_task = task
        return test_run

    async def _run_pipeline(self, project: Project, test_run: TestRun, test_cases: List[TestCase]):
        run_id = test_run.id
        evidence_dir = settings.EVIDENCE_DIR / test_run.run_number
        evidence_dir.mkdir(parents=True, exist_ok=True)

        session_deadline = (
            datetime.datetime.now(datetime.timezone.utc).timestamp()
            + settings.MAX_TEST_TIME
        )
        try:
            await self._execute_pipeline(project, test_run, test_cases, session_deadline, evidence_dir=evidence_dir)
        except asyncio.CancelledError:
            await self._fail_run(test_run, "Pipeline cancelled.")
            raise
        except Exception as e:
            logger.exception("Pipeline crashed for run %s", run_id)
            await self._fail_run(test_run, str(e))

    async def _fail_run(self, test_run: TestRun, error_message: str):
        """Mark a run as failed and persist the error."""
        test_run.status = "FAILED"
        test_run.error_message = error_message
        test_run.completed_at = datetime.datetime.now(datetime.timezone.utc)
        await self.db.commit()
        await self._emit_log(test_run.id, f"✗ Pipeline failed: {error_message}", status="error")

    async def _execute_pipeline(
        self,
        project: Project,
        test_run: TestRun,
        test_cases: List[TestCase],
        session_deadline: float,
        evidence_dir: Path = None,
    ):
        run_id = test_run.id
        await self._emit_log(run_id, "✓ Repository cloned", status="success")
        await self._emit_log(run_id, "✓ Git repository verified", status="success")
        stack = project.tech_stack or {}
        await self._emit_log(run_id, f"✓ Frontend detected: {stack.get('frontend', 'Not detected')}", status="success")
        await self._emit_log(run_id, f"✓ Backend detected: {stack.get('backend', 'Not detected')}", status="success")
        await self._emit_log(run_id, f"✓ Database detected: {stack.get('database', 'Not detected')}", status="success")
        await self._emit_log(run_id, f"✓ {stack.get('api_count', 0)} API endpoints and {stack.get('route_count', 0)} frontend routes discovered", status="success")
        await self._emit_log(run_id, f"✓ {len(project.modules or [])} repository modules discovered", status="success")

        start_cmd = project.startup_command
        if start_cmd and not validate_startup_command(start_cmd)[0]:
            start_cmd = None

        # Start target application with dynamic runtime discovery & fallback
        app_runner = ApplicationRunner(
            repo_dir=Path(project.local_path or settings.TEMP_REPO_DIR / project.id),
            startup_command=start_cmd,
            target_port=project.app_port,
            startup_timeout=settings.APP_STARTUP_TIMEOUT,
        )

        app_started, app_url, is_fallback, app_msg, real_target_available = await app_runner.start()
        runtime_context = RuntimeContext(
            frontend_base_url=app_url,
            backend_base_url=app_url,
            api_base_url=app_url,
            services=[{"name": "target", "base_url": app_url, "status": "READY" if app_started else "UNAVAILABLE"}],
        )
        project.app_url = app_url
        await self.db.commit()

        if app_started and not is_fallback and real_target_available:
            await self._emit_log(run_id, f"✓ Target application started on {app_url}", status="success")
        else:
            if is_fallback:
                fallback_reason = f" ({app_msg})" if app_msg else ""
                await self._emit_log(run_id, f"⚠ Static fallback server active{fallback_reason} on {app_url}. Not the real Spring Boot target.", status="warning")
            else:
                await self._emit_log(run_id, f"⚠ Target application failed to start: {app_msg or 'Unreachable'}", status="warning")

        # Allow local/offline fallback runs to continue instead of hard-blocking the QA pipeline.
        # A fallback owns the test URL even when its readiness probe reports a soft failure.
        if not app_started and not is_fallback:
            await self._emit_log(run_id, "[BLOCKED] Backend startup blocked: Target application unavailable", status="blocking")
            await self._emit_log(run_id, "[BLOCKED] Real target application was not started", status="blocking")
            await self._emit_log(run_id, "[EXECUTION] API tests: BLOCKED", status="blocking")
            await self._emit_log(run_id, "[EXECUTION] Browser tests: BLOCKED", status="blocking")

            n_cases = len(test_cases)
            for tc in test_cases:
                await self.db.add(TestExecutionResult(
                    run_id=test_run.id,
                    test_case_id=tc.id,
                    status="BLOCKED",
                    duration=0.0,
                    actual_result=f"Blocked: Real target application was not started. {app_msg or ''}".strip(),
                    stdout="",
                ))

            test_run.status = "BLOCKED"
            test_run.total_tests = n_cases
            test_run.passed_tests = 0
            test_run.failed_tests = 0
            test_run.blocked_tests = n_cases
            test_run.completed_at = datetime.datetime.now(datetime.timezone.utc)
            await self.db.commit()

            await self._emit_log(run_id, "[REPORT] Executed: 0", status="info")
            await self._emit_log(run_id, "[REPORT] Passed: 0", status="info")
            await self._emit_log(run_id, "[REPORT] Failed: 0", status="info")
            await self._emit_log(run_id, f"[REPORT] Blocked: {n_cases}", status="info")
            await self._emit_log(run_id, "[REPORT] Pass Rate: N/A", status="error")
            await self._emit_log(run_id, "[REPORT] Release Recommendation: NOT ASSESSED", status="error")
            await self._emit_log(run_id, "Test Run Completed — BLOCKED (startup failure)", status="error")
            return

        # Initialize Playwright Browser Agent
        browser_agent = BrowserAgent(
            run_id=test_run.run_number,
            evidence_dir=evidence_dir,
            step_timeout=settings.BROWSER_STEP_TIMEOUT_MS,
        )
        await browser_agent.start_browser(headless=True)
        await self._emit_log(run_id, "✓ Browser initialized (Playwright Chromium)", status="success")

        passed_count = 0
        failed_count = 0
        bug_engine = BugEngine()
        failure_analyzer = FailureAnalyzer()
        bug_index = 1

        for tc in test_cases:
            # Enforce overall session deadline
            if datetime.datetime.now(datetime.timezone.utc).timestamp() > session_deadline:
                await self._emit_log(run_id, f"⚠ Session deadline reached; skipping {tc.test_id}", status="warning")
                self.db.add(TestExecutionResult(
                    run_id=test_run.id,
                    test_case_id=tc.id,
                    status="SKIPPED",
                    duration=0.0,
                    actual_result="Skipped due to session deadline.",
                    stdout="",
                ))
                continue

            await self._emit_log(run_id, f"Running {tc.test_id}: {tc.title}...", status="running")
            start_time = datetime.datetime.now(datetime.timezone.utc)

            tc_success = True
            error_msg = ""
            result_validity = "VALID"
            assertion_evaluated = False
            stdout_logs = []
            screenshot_paths = []

            if tc.test_type == "api":
                endpoint_registry = {
                    (item.get("method", "").upper(), item.get("path", "").rstrip("/"))
                    for item in (project.tech_stack or {}).get("api_endpoints", [])
                }
                for step in tc.steps:
                    step_method = (step.get("action") or "").replace("http_", "").upper()
                    step_path = (step.get("target") or "/").rstrip("/")
                    if (step_method, step_path) not in endpoint_registry:
                        tc_success = False
                        result_validity = "INVALID_TEST"
                        error_msg = f"API endpoint {step_method} {step_path} is not present in the repository endpoint registry."
                        break

            # Execute steps with per-test-case timeout guard
            case_deadline = start_time.timestamp() + settings.MAX_TEST_TIME
            try:
                if not tc_success:
                    pass
                elif tc.test_type == "api":
                    for step in tc.steps:
                        step_ok, step_msg, duration = await APITester.execute_api_test(step, runtime_context)
                        assertion_evaluated = True
                        stdout_logs.append(step_msg)
                        if not step_ok:
                            tc_success = False
                            error_msg = step_msg
                            if "Invalid test target" in step_msg or "outside the current runtime" in step_msg:
                                result_validity = "INVALID_TARGET"
                            break
                else:
                    for step in tc.steps:
                        action = (step.get("action") or "").lower()
                        step_ok, step_msg, shot_path = await browser_agent.execute_step(step, runtime_context)
                        stdout_logs.append(step_msg)
                        if action in {"open_url", "get_page_title", "title"}:
                            assertion_evaluated = True
                        if shot_path:
                            screenshot_paths.append(shot_path)
                        if not step_ok:
                            tc_success = False
                            error_msg = step_msg
                            if "Invalid test target" in step_msg or "outside the current runtime" in step_msg:
                                result_validity = "INVALID_TARGET"
                            break
            except asyncio.TimeoutError:
                tc_success = False
                error_msg = "Test case timed out."

            if tc_success and not assertion_evaluated:
                tc_success = False
                result_validity = "UNVERIFIED"
                error_msg = "Test completed without an evaluated assertion."

            duration_sec = (datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds()

            if tc_success:
                passed_count += 1
                await self._emit_log(run_id, f"✓ {tc.test_id} passed ({duration_sec:.2f}s)", status="success")
                db_result = TestExecutionResult(
                    run_id=test_run.id,
                    test_case_id=tc.id,
                    status="PASSED",
                    duration=duration_sec,
                    actual_result="Test executed cleanly as expected.",
                    result_validity=result_validity,
                    stdout="\n".join(stdout_logs)
                )
            else:
                failed_count += 1
                await self._emit_log(run_id, f"✗ {tc.test_id} failed", status="error")
                await self._emit_log(run_id, "Collecting evidence...", status="info")
                await self._emit_log(run_id, "Analyzing failure with LLM...", status="info")

                # Perform failure analysis
                failure_context = {
                    "test_case_id": tc.test_id,
                    "title": tc.title,
                    "expected_result": tc.expected_result,
                    "error_message": error_msg,
                    "console_logs": browser_agent.console_logs,
                    "network_requests": browser_agent.network_requests
                }
                analysis = await failure_analyzer.analyze_failure(failure_context)

                # Create Bug report if classified as defect
                if analysis.classification in ["APPLICATION_BUG", "DEPENDENCY_FAILURE", "UNKNOWN"]:
                    await self._emit_log(run_id, f"Defect detected ({analysis.classification}) - Creating bug report", status="warning")
                    bug_dict = bug_engine.create_bug_report(
                        bug_index=bug_index,
                        run_id=test_run.id,
                        test_case={"id": tc.id, "title": tc.title, "module": tc.module, "steps": tc.steps, "expected_result": tc.expected_result, "priority": tc.priority, "risk": tc.risk},
                        actual_error=error_msg,
                        analysis=analysis,
                        evidence_paths=screenshot_paths
                    )
                    db_bug = Bug(**bug_dict)
                    self.db.add(db_bug)
                    bug_index += 1

                db_result = TestExecutionResult(
                    run_id=test_run.id,
                    test_case_id=tc.id,
                    status="UNVERIFIED" if result_validity == "UNVERIFIED" else "FAILED",
                    duration=duration_sec,
                    actual_result=error_msg,
                    error_message=error_msg,
                    result_validity=result_validity,
                    stdout="\n".join(stdout_logs)
                )

            db_result.attempt_number = 1

            self.db.add(db_result)
            await self.db.commit()

        # Teardown browser & app runner
        await browser_agent.close()
        app_runner.stop()

        # Finalize TestRun status
        test_run.status = "COMPLETED"
        test_run.completed_at = datetime.datetime.now(datetime.timezone.utc)
        result_rows = await self.db.execute(select(TestExecutionResult.status).where(TestExecutionResult.run_id == test_run.id))
        result_statuses = [status for (status,) in result_rows.all()]
        test_run.total_tests = len(result_statuses)
        test_run.passed_tests = result_statuses.count("PASSED")
        test_run.failed_tests = result_statuses.count("FAILED")
        test_run.blocked_tests = result_statuses.count("BLOCKED") + result_statuses.count("SKIPPED") + result_statuses.count("ERROR")
        await self.db.commit()

        # Generate QA Report
        await self._emit_log(run_id, "Generating final QA Report...", status="info")
        executed_count = test_run.passed_tests + test_run.failed_tests
        if executed_count > 0:
            final_pass_rate = round((test_run.passed_tests / executed_count) * 100, 1)
            await self._emit_log(run_id, f"Test Run Completed. Pass Rate: {final_pass_rate}%", status="success")
        else:
            await self._emit_log(run_id, "Test Run Completed. Pass Rate: N/A", status="warning")
            await self._emit_log(run_id, "Release Recommendation: NOT ASSESSED", status="warning")

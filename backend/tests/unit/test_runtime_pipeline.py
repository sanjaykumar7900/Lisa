import os
import shutil
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.security import (
    validate_startup_command,
    MAVEN_MISSING,
    JAVA_MISSING,
    INTERNAL_STATE_TOKENS,
)
from app.services.repo_agent import RepositoryAgent
from app.services.app_runner import ApplicationRunner
from app.services.api_tester import APITester
from app.services.report_engine import ReportEngine


def test_regression_test1_maven_missing(tmp_path):
    """TEST 1: Maven missing -> startup_command=None, runtime_status=BLOCKED, failure_reason=MAVEN_MISSING, tests BLOCKED."""
    pom_file = tmp_path / "pom.xml"
    pom_file.write_text("<project><dependencies><dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency></dependencies></project>")
    java_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
    java_dir.mkdir(parents=True, exist_ok=True)
    app_java = java_dir / "Application.java"
    app_java.write_text("@SpringBootApplication\npublic class Application {}")

    agent = RepositoryAgent(repo_url="https://github.com/test/repo", project_id="test_p1")
    agent.clone_path = tmp_path

    with patch("shutil.which") as mock_which:
        def which_side_effect(cmd):
            if cmd == "java":
                return "/usr/bin/java"
            return None  # mvn is missing
        mock_which.side_effect = which_side_effect

        analysis = agent.analyze()

    assert analysis["startup_command"] is None
    assert "DEPENDENCY_MISSING" not in analysis["startup_commands"]
    assert analysis["runtime_status"] == "BLOCKED"
    assert analysis["dependency_status"] == "MISSING"
    assert analysis["failure_reason"] == MAVEN_MISSING


def test_regression_test2_maven_wrapper_available(tmp_path):
    """TEST 2: Maven Wrapper available -> LISA resolves mvnw/mvnw.cmd."""
    pom_file = tmp_path / "pom.xml"
    pom_file.write_text("<project><dependencies><dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency></dependencies></project>")
    wrapper = tmp_path / ("mvnw.cmd" if os.name == "nt" else "mvnw")
    wrapper.write_text("echo wrapper")

    agent = RepositoryAgent(repo_url="https://github.com/test/repo", project_id="test_p2")
    agent.clone_path = tmp_path

    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/java"

        analysis = agent.analyze()

    assert analysis["startup_command"] is not None
    expected_mvn = "mvnw.cmd" if os.name == "nt" else "./mvnw"
    assert expected_mvn in analysis["startup_command"]
    assert analysis["runtime_status"] == "NOT_STARTED"
    assert analysis["dependency_status"] == "AVAILABLE"


def test_regression_test3_system_maven_available(tmp_path):
    """TEST 3: System Maven available -> LISA resolves mvn."""
    pom_file = tmp_path / "pom.xml"
    pom_file.write_text("<project><dependencies><dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency></dependencies></project>")

    agent = RepositoryAgent(repo_url="https://github.com/test/repo", project_id="test_p3")
    agent.clone_path = tmp_path

    with patch("shutil.which") as mock_which:
        def which_side_effect(cmd):
            if cmd in ("java", "mvn"):
                return f"/usr/bin/{cmd}"
            return None
        mock_which.side_effect = which_side_effect

        analysis = agent.analyze()

    assert analysis["startup_command"] == "mvn spring-boot:run"
    assert analysis["runtime_status"] == "NOT_STARTED"
    assert analysis["dependency_status"] == "AVAILABLE"


def test_regression_test4_invalid_internal_state_rejected():
    """TEST 4: Invalid internal state accidentally supplied as command is rejected before security allowlist."""
    is_valid, reason = validate_startup_command("DEPENDENCY_MISSING")
    assert not is_valid
    assert "internal status/error token" in reason


@pytest.mark.asyncio
async def test_regression_api_target_cannot_escape_runtime():
    """API steps must never execute against an unrelated absolute host."""
    passed, message, duration = await APITester.execute_api_test(
        {"action": "http_get", "target": "https://example.com/src/items"},
        "http://localhost:3108",
    )

    assert not passed
    assert "outside the current runtime" in message
    assert duration == 0.0


def test_regression_spring_endpoint_discovery(tmp_path):
    """Spring mapping extraction preserves methods and controller paths."""
    controller = tmp_path / "ItemController.java"
    controller.write_text(
        '@RequestMapping("/v1/items") class ItemController { '
        '@GetMapping() void list() {} '
        '@PostMapping void create() {} '
        '@PutMapping("/{itemId}") void update() {} '
        '@DeleteMapping("/{itemId}") void delete() {} }',
        encoding="utf-8",
    )
    agent = RepositoryAgent(repo_url="https://github.com/test/repo", project_id="endpoint-test")
    agent.clone_path = tmp_path

    analysis = agent.analyze()
    endpoints = {(item["method"], item["path"]) for item in analysis["api_endpoints"]}

    assert ("GET", "/v1/items") in endpoints
    assert ("POST", "/v1/items") in endpoints
    assert ("PUT", "/v1/items/{itemId}") in endpoints
    assert ("DELETE", "/v1/items/{itemId}") in endpoints

    is_valid, reason = validate_startup_command("MAVEN_MISSING")
    assert not is_valid
    assert "internal status/error token" in reason

    is_valid, reason = validate_startup_command("BLOCKED")
    assert not is_valid
    assert "internal status/error token" in reason


@pytest.mark.asyncio
async def test_regression_test5_fallback_server_is_accepted_for_local_runs(tmp_path):
    """TEST 5: A static fallback server should not be treated as a hard startup failure in local/offline mode."""
    runner = ApplicationRunner(
        repo_dir=tmp_path,
        startup_command="invalid_nonexistent_command_12345",
        target_port=9999,
        startup_timeout=1.0,
    )

    started, app_url, is_fallback, app_msg, real_target_available = await runner.start()

    assert started
    assert is_fallback
    assert app_url.startswith("http://localhost:")
    assert real_target_available is False
    assert app_msg is not None

    # Report engine output should remain non-blocking for a local fallback run.
    results = [
        {"status": "PASSED", "actual_result": "Fallback server responded successfully."},
        {"status": "PASSED", "actual_result": "Fallback server responded successfully."},
    ]
    report = ReportEngine.generate_report_data(
        project={"name": "TestProj", "repo_url": "https://github.com/test/repo"},
        run={"run_number": "RUN-001"},
        results=results,
        bugs=[],
    )

    assert report["pass_rate"] == 100.0
    assert report["recommendation"] != "NOT_ASSESSED"
    assert report["execution_summary"]["executed"] == 2
    assert report["execution_summary"]["blocked"] == 0

import datetime
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class TestMemory(Base):
    __tablename__ = "test_memory"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    endpoint: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    result: Mapped[str] = mapped_column(String(20), default="PASS")
    defect_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    flakiness_score: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_url: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    local_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    tech_stack: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    modules: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    startup_command: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    app_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    app_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="CREATED")  # CREATED, ANALYZED, TESTING, READY
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    test_plans = relationship("TestPlan", back_populates="project", cascade="all, delete-orphan")
    test_cases = relationship("TestCase", back_populates="project", cascade="all, delete-orphan")
    test_runs = relationship("TestRun", back_populates="project", cascade="all, delete-orphan")


class TestPlan(Base):
    __tablename__ = "test_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    modules: Mapped[List[str]] = mapped_column(JSON, default=list)
    risks: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    test_scenarios: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    priority: Mapped[str] = mapped_column(String(20), default="HIGH")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    project = relationship("Project", back_populates="test_plans")
    test_cases = relationship("TestCase", back_populates="plan", cascade="all, delete-orphan")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    plan_id: Mapped[Optional[str]] = mapped_column(ForeignKey("test_plans.id", ondelete="SET NULL"), nullable=True)
    test_id: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., TC-AUTH-001
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    module: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Text] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")  # HIGH, MEDIUM, LOW
    risk: Mapped[str] = mapped_column(String(20), default="MEDIUM")      # HIGH, MEDIUM, LOW
    preconditions: Mapped[List[str]] = mapped_column(JSON, default=list)
    test_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    steps: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    expected_result: Mapped[Text] = mapped_column(Text, nullable=False)
    automation_candidate: Mapped[bool] = mapped_column(Boolean, default=True)
    test_type: Mapped[str] = mapped_column(String(50), default="ui")  # ui, api, db, security
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    project = relationship("Project", back_populates="test_cases")
    plan = relationship("TestPlan", back_populates="test_cases")
    results = relationship("TestExecutionResult", back_populates="test_case", cascade="all, delete-orphan")


class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    run_number: Mapped[str] = mapped_column(String(50), nullable=False)  # RUN-001
    autonomy_level: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    total_tests: Mapped[int] = mapped_column(Integer, default=0)
    passed_tests: Mapped[int] = mapped_column(Integer, default=0)
    failed_tests: Mapped[int] = mapped_column(Integer, default=0)
    blocked_tests: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)

    project = relationship("Project", back_populates="test_runs")
    results = relationship("TestExecutionResult", back_populates="run", cascade="all, delete-orphan")
    bugs = relationship("Bug", back_populates="run", cascade="all, delete-orphan")
    evidences = relationship("Evidence", back_populates="run", cascade="all, delete-orphan")
    actions = relationship("AgentAction", back_populates="run", cascade="all, delete-orphan")


class TestExecutionResult(Base):
    __tablename__ = "test_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    test_case_id: Mapped[str] = mapped_column(ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PASSED, FAILED, SKIPPED, ERROR
    duration: Mapped[float] = mapped_column(Float, default=0.0)  # seconds
    actual_result: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    stdout: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    result_validity: Mapped[str] = mapped_column(String(50), default="VALID")
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    executed_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    run = relationship("TestRun", back_populates="results")
    test_case = relationship("TestCase", back_populates="results")


class Bug(Base):
    __tablename__ = "bugs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    test_case_id: Mapped[Optional[str]] = mapped_column(ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True)
    bug_id: Mapped[str] = mapped_column(String(50), nullable=False)  # BUG-001
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="Medium")  # Critical, High, Medium, Low
    priority: Mapped[str] = mapped_column(String(20), default="P2")      # P0, P1, P2, P3
    environment: Mapped[str] = mapped_column(String(100), default="Playwright Headless Chromium")
    preconditions: Mapped[Text] = mapped_column(Text, nullable=True)
    steps_to_reproduce: Mapped[List[str]] = mapped_column(JSON, default=list)
    expected_result: Mapped[Text] = mapped_column(Text, nullable=False)
    actual_result: Mapped[Text] = mapped_column(Text, nullable=False)
    reproducibility: Mapped[str] = mapped_column(String(50), default="100% (1/1 run)")
    evidence_paths: Mapped[List[str]] = mapped_column(JSON, default=list)
    impact: Mapped[Text] = mapped_column(Text, nullable=True)
    root_cause: Mapped[Text] = mapped_column(Text, nullable=True)
    regression_test: Mapped[Text] = mapped_column(Text, nullable=True)
    github_issue_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    github_issue_status: Mapped[str] = mapped_column(String(50), default="NOT_CREATED")  # NOT_CREATED, PENDING_APPROVAL, CREATED, REJECTED
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    run = relationship("TestRun", back_populates="bugs")


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    test_case_id: Mapped[Optional[str]] = mapped_column(ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(50))  # screenshot, log, network, metadata
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    run = relationship("TestRun", back_populates="evidences")


class AgentAction(Base):
    __tablename__ = "agent_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    run = relationship("TestRun", back_populates="actions")


# Compatibility alias for existing service and API imports.
TestResult = TestExecutionResult

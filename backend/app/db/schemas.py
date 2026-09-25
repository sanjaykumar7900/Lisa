from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict

class ProjectCreate(BaseModel):
    repo_url: str
    name: Optional[str] = None
    startup_command: Optional[str] = None
    app_port: Optional[int] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    repo_url: str
    local_path: Optional[str] = None
    tech_stack: Optional[Dict[str, Any]] = None
    modules: Optional[List[Dict[str, Any]]] = None
    startup_command: Optional[str] = None
    app_port: Optional[int] = None
    app_url: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TestStep(BaseModel):
    step_number: int
    action: str
    target: Optional[str] = ""
    value: Optional[str] = None
    expected: Optional[str] = None
    expected_status: Optional[int] = None
    assertions: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(extra="allow")

class TestCaseCreate(BaseModel):
    test_id: str
    title: str
    module: str
    description: str
    priority: str = "MEDIUM"
    risk: str = "MEDIUM"
    preconditions: List[str] = []
    test_data: Dict[str, Any] = {}
    steps: List[TestStep] = []
    expected_result: str
    automation_candidate: bool = True
    test_type: str = "ui"

class TestCaseResponse(BaseModel):
    id: str
    project_id: str
    plan_id: Optional[str] = None
    test_id: str
    title: str
    module: str
    description: str
    priority: str
    risk: str
    preconditions: List[str]
    test_data: Dict[str, Any]
    steps: List[Dict[str, Any]]
    expected_result: str
    automation_candidate: bool
    test_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TestPlanResponse(BaseModel):
    id: str
    project_id: str
    modules: List[str]
    risks: List[Dict[str, Any]]
    test_scenarios: List[Dict[str, Any]]
    priority: str
    created_at: datetime
    test_cases: List[TestCaseResponse] = []

    model_config = ConfigDict(from_attributes=True)

class TestRunCreate(BaseModel):
    autonomy_level: int = 3
    test_case_ids: Optional[List[str]] = None
    test_options: Optional[Dict[str, Any]] = None  # User-selected dropdown options: test_types, scopes, etc.

class TestRunResponse(BaseModel):
    id: str
    project_id: str
    run_number: str
    autonomy_level: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_tests: int
    passed_tests: int
    failed_tests: int
    blocked_tests: int = 0
    result_validity: Optional[str] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class BugResponse(BaseModel):
    id: str
    run_id: str
    test_case_id: Optional[str] = None
    bug_id: str
    title: str
    severity: str
    priority: str
    environment: str
    preconditions: Optional[str] = None
    steps_to_reproduce: List[str]
    expected_result: str
    actual_result: str
    reproducibility: str
    evidence_paths: List[str]
    impact: Optional[str] = None
    root_cause: Optional[str] = None
    regression_test: Optional[str] = None
    github_issue_url: Optional[str] = None
    github_issue_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EvidenceResponse(BaseModel):
    id: str
    run_id: str
    test_case_id: Optional[str] = None
    type: str
    path: str
    metadata_json: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

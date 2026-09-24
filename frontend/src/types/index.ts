export interface Project {
  id: string;
  name: string;
  repo_url: string;
  local_path?: string;
  tech_stack?: {
    languages?: string[];
    frontend?: string;
    backend?: string;
    database?: string;
    build_tool?: string;
    package_manager?: string;
    test_framework?: string;
    api_available?: boolean;
    application_type?: string;
    startup_commands?: string[];
    readme_snippet?: string;
    orm?: string;
    evidence?: Record<string, string[]>;
    architecture?: Array<{ label: string; technology?: string; evidence?: string[] }>;
    ports?: Array<{ name: string; technology: string; port: number; source: string }>;
    route_count?: number;
    api_count?: number;
  };
  modules?: Array<{
    name: string;
    path: string;
    files_count: number;
    sample_files: string[];
    role?: string;
    routes_count?: number;
    components_count?: number;
    controllers_count?: number;
    services_count?: number;
    repositories_count?: number;
    api_count?: number;
  }>;
  startup_command?: string;
  app_port?: number;
  app_url?: string;
  status: 'CREATED' | 'ANALYZING' | 'ANALYZED' | 'TESTING' | 'READY';
  created_at: string;
}

export interface TestCase {
  id: string;
  project_id: string;
  plan_id?: string;
  test_id: string;
  title: string;
  module: string;
  description: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  risk: 'HIGH' | 'MEDIUM' | 'LOW';
  preconditions: string[];
  test_data: Record<string, any>;
  steps: Array<{
    step_number: number;
    action: string;
    target: string;
    value?: string;
    expected?: string;
  }>;
  expected_result: string;
  automation_candidate: boolean;
  test_type: 'ui' | 'api' | 'db' | 'security';
  created_at: string;
}

export interface TestPlan {
  id: string;
  project_id: string;
  modules: string[];
  risks: Array<{ component: string; risk_level: string; description: string }>;
  test_scenarios: Array<{ id: string; title: string; module: string }>;
  priority: string;
  created_at: string;
  test_cases: TestCase[];
}

export interface TestRun {
  id: string;
  project_id: string;
  run_number: string;
  autonomy_level: number;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  started_at?: string;
  completed_at?: string;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  blocked_tests: number;
  error_message?: string;
}

export interface Bug {
  id: string;
  run_id: string;
  test_case_id?: string;
  bug_id: string;
  title: string;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  priority: 'P0' | 'P1' | 'P2' | 'P3';
  environment: string;
  preconditions?: string;
  steps_to_reproduce: string[];
  expected_result: string;
  actual_result: string;
  reproducibility: string;
  evidence_paths: string[];
  impact?: string;
  root_cause?: string;
  regression_test?: string;
  github_issue_url?: string;
  github_issue_status: 'NOT_CREATED' | 'PENDING_APPROVAL' | 'CREATED' | 'REJECTED';
  created_at: string;
}

export interface QAReport {
  executive_summary: string;
  pass_rate: number | null;
  recommendation: 'PASS' | 'CONDITIONAL PASS' | 'FAIL' | 'BLOCKED' | 'NOT_ASSESSED';
  recommendation_reasoning: string;
  test_coverage: string;
  automation_coverage: string;
  generated_at: string;
  html_report?: string;
  blocked_tests?: number;
  execution_summary?: { total: number; executed?: number; passed: number; failed: number; blocked: number; pass_rate: number | null };
  repository_information?: Record<string, unknown>;
  detected_technology_stack?: Project['tech_stack'];
  architecture?: Array<{ label: string; technology?: string; evidence?: string[] }>;
  discovered_modules?: Project['modules'];
  test_strategy?: string;
  code_coverage?: string;
  recommendations?: string[];
}

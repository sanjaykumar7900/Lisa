import type { Project, TestPlan, TestRun, Bug, QAReport } from '../types';
import { ApiError, classifyError } from './errors';

const API_BASE = '/api/v1';

async function parseResponseError(res: Response, fallback: string, endpoint?: string, method?: string): Promise<never> {
  const text = await res.text().catch(() => '');
  const status = res.status;
  let detail = '';
  try {
    const data = JSON.parse(text);
    detail = data.detail || data.message || '';
  } catch {
    detail = text.length < 200 && text.trim().length > 0 ? text.trim() : '';
  }

  if (status === 404) throw new ApiError('ENDPOINT_NOT_FOUND', `API endpoint not found: ${endpoint || 'unknown'} (HTTP 404)`, { status, endpoint, method, details: detail, retryable: false });
  if (status === 401) throw new ApiError('AUTHENTICATION_ERROR', 'Authentication failed.', { status, endpoint, method, details: detail, retryable: false });
  if (status === 403) throw new ApiError('AUTHORIZATION_ERROR', 'Access denied.', { status, endpoint, method, details: detail, retryable: false });
  if (status === 422) throw new ApiError('VALIDATION_ERROR', 'Invalid request.', { status, endpoint, method, details: detail, retryable: false });
  if (status === 500) throw new ApiError('BACKEND_INTERNAL_ERROR', 'LISA backend returned an internal server error.', { status, endpoint, method, details: detail, retryable: true });
  if (status === 502 || status === 503 || status === 504) throw new ApiError('SERVICE_UNAVAILABLE', 'Service temporarily unavailable.', { status, endpoint, method, details: detail, retryable: true });
  if (status === 400) throw new ApiError('HTTP_400', 'Bad request.', { status, endpoint, method, details: detail, retryable: false });
  if (status === 409) throw new ApiError('HTTP_409', 'Conflict.', { status, endpoint, method, details: detail, retryable: false });
  if (status === 429) throw new ApiError('HTTP_429', 'Rate limited.', { status, endpoint, method, details: detail, retryable: true });

  throw new ApiError('UNKNOWN_ERROR', `${fallback} (HTTP ${status})`, { status, endpoint, method, details: detail, retryable: false });
}

async function parseResponse<T>(res: Response, fallback: string, endpoint?: string, method?: string): Promise<T> {
  if (!res.ok) {
    await parseResponseError(res, fallback, endpoint, method);
  }
  return res.json();
}

async function fetchJson<T>(url: string, fallback: string, options?: RequestInit): Promise<T> {
  const endpoint = url;
  const method = options?.method || 'GET';
  try {
    const res = await fetch(url, options);
    return await parseResponse<T>(res, fallback, endpoint, method);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    const classified = classifyError(error, endpoint, method);
    throw classified;
  }
}

export async function fetchProjects(): Promise<Project[]> {
  return fetchJson<Project[]>(`${API_BASE}/projects`, 'Failed to fetch projects');
}

export async function createProject(repo_url: string, name?: string): Promise<Project> {
  return fetchJson<Project>(`${API_BASE}/projects`, 'Failed to create project', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url, name })
  });
}

export async function deleteProject(projectId: string): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/projects/${projectId}`, { method: 'DELETE' });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      let detail = '';
      try { const data = JSON.parse(text); detail = data.detail || ''; } catch { detail = text.length < 200 && text.trim().length > 0 ? text.trim() : ''; }
      const status = res.status;
      if (status === 404) throw new ApiError('ENDPOINT_NOT_FOUND', `Project not found (HTTP 404)`, { status, endpoint: `/projects/${projectId}`, method: 'DELETE', details: detail });
      if (status === 401) throw new ApiError('AUTHENTICATION_ERROR', 'Authentication failed.', { status, endpoint: `/projects/${projectId}`, method: 'DELETE', details: detail });
      if (status === 403) throw new ApiError('AUTHORIZATION_ERROR', 'Access denied.', { status, endpoint: `/projects/${projectId}`, method: 'DELETE', details: detail });
      if (status === 422) throw new ApiError('VALIDATION_ERROR', 'Invalid request.', { status, endpoint: `/projects/${projectId}`, method: 'DELETE', details: detail });
      if (status === 500) throw new ApiError('BACKEND_INTERNAL_ERROR', 'LISA backend returned an internal server error.', { status, endpoint: `/projects/${projectId}`, method: 'DELETE', details: detail, retryable: true });
      throw new ApiError('UNKNOWN_ERROR', `Failed to delete project (HTTP ${status})`, { status, endpoint: `/projects/${projectId}`, method: 'DELETE', details: detail });
    }
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw classifyError(error, `/projects/${projectId}`, 'DELETE');
  }
}

export async function analyzeProject(projectId: string): Promise<Project> {
  return fetchJson<Project>(`${API_BASE}/projects/${projectId}/analyze`, 'Failed to analyze project', { method: 'POST' });
}

export async function generateTestPlan(projectId: string): Promise<TestPlan> {
  return fetchJson<TestPlan>(`${API_BASE}/projects/${projectId}/test-plan`, 'Failed to generate test plan', { method: 'POST' });
}

export async function startTestRun(projectId: string, autonomyLevel = 3, testOptions?: any): Promise<TestRun> {
  return fetchJson<TestRun>(`${API_BASE}/projects/${projectId}/test`, 'Failed to start test run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ autonomy_level: autonomyLevel, test_options: testOptions })
  });
}

export async function fetchTestRuns(): Promise<TestRun[]> {
  return fetchJson<TestRun[]>(`${API_BASE}/test-runs`, 'Failed to fetch test runs');
}

export async function fetchBugs(): Promise<Bug[]> {
  return fetchJson<Bug[]>(`${API_BASE}/bugs`, 'Failed to fetch bugs');
}

export async function approveGithubIssue(bugId: string): Promise<any> {
  return fetchJson<any>(`${API_BASE}/bugs/${bugId}/approve-issue`, 'Failed to approve issue', { method: 'POST' });
}

export async function fetchReport(runId: string): Promise<QAReport> {
  return fetchJson<QAReport>(`${API_BASE}/reports/${runId}`, 'Failed to fetch report');
}

export async function downloadTestResults(runId: string): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/test-runs/${runId}/results.csv`);
    if (!response.ok) {
      await parseResponseError(response, 'Failed to download', `/test-runs/${runId}/results.csv`, 'GET');
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `test-results-${runId}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw classifyError(error, `/test-runs/${runId}/results.csv`, 'GET');
  }
}

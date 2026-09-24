import type { Project, TestPlan, TestRun, Bug, QAReport } from '../types';

const API_BASE = '/api/v1';

function toFriendlyApiError(message: string, fallbackErrorMsg: string): Error {
  const lower = message.toLowerCase();

  if (lower.includes('not found') || lower.includes('failed to fetch') || lower.includes('load failed')) {
    return new Error('LISA backend is unavailable. Start the backend server and try again.');
  }

  if (lower.includes('invalid or missing api key')) {
    return new Error('The backend rejected the request because the API key is missing or invalid.');
  }

  return new Error(message || fallbackErrorMsg);
}

async function parseResponse<T>(res: Response, fallbackErrorMsg: string): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    let detail = '';
    try {
      const data = JSON.parse(text);
      detail = data.detail || data.message || '';
    } catch {
      detail = text.length < 200 && text.trim().length > 0 ? text.trim() : '';
    }

    const message = detail || `${fallbackErrorMsg} (HTTP ${res.status})`;
    throw toFriendlyApiError(message, fallbackErrorMsg);
  }
  return res.json();
}

async function fetchJson<T>(url: string, fallbackErrorMsg: string, options?: RequestInit): Promise<T> {
  try {
    const res = await fetch(url, options);
    return await parseResponse<T>(res, fallbackErrorMsg);
  } catch (error) {
    if (error instanceof Error) {
      throw toFriendlyApiError(error.message, fallbackErrorMsg);
    }
    throw new Error(fallbackErrorMsg);
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
      try {
        const data = JSON.parse(text);
        detail = data.detail || '';
      } catch {
        detail = text.length < 200 && text.trim().length > 0 ? text.trim() : '';
      }
      throw toFriendlyApiError(detail || `Failed to delete project (HTTP ${res.status})`, 'Failed to delete project');
    }
  } catch (error) {
    if (error instanceof Error) {
      throw toFriendlyApiError(error.message, 'Failed to delete project');
    }
    throw new Error('Failed to delete project');
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
  const response = await fetch(`${API_BASE}/test-runs/${runId}/results.csv`);
  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw toFriendlyApiError(text || `Failed to download test results (HTTP ${response.status})`, 'Failed to download test results');
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
}

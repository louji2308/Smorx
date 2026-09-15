const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'API request failed');
  }
  return res.json();
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  description: string;
  created_at: string;
}

export interface Repository {
  id: string;
  project_id: string;
  name: string;
  url: string;
  default_branch: string;
  meta?: Record<string, any>;
}

export interface Change {
  id: string;
  repository_id: string;
  external_id: string;
  title: string;
  description: string;
  commit_sha: string;
  status: string;
}

export interface WorkflowResult {
  project: Project;
  repository: Repository;
  change: Change;
  constitution: { id: string; title: string; status: string; claimCount: number; protectedCount: number };
  analysis: Record<string, any>;
  intents: Array<{ statement: string; kind: string; priority: string; source_ref: string }>;
  impact: { surfaces: Array<{ path: string; direction: string; risk: string }>; risk_zones: Array<{ pattern: string; reason: string; severity: string }>; summary: string };
}

export const api = {
  health: () => apiFetch<{ status: string }>('/health'),

  startWorkflow: (data: {
    project_name: string;
    repo_url: string;
    change_title: string;
    change_description?: string;
    change_author?: string;
  }) => apiFetch<WorkflowResult>('/api/workflow/start', { method: 'POST', body: JSON.stringify(data) }),

  listProjects: () => apiFetch<Project[]>('/api/projects'),
  createProject: (data: { name: string; slug: string; description?: string }) =>
    apiFetch<Project>('/api/projects', { method: 'POST', body: JSON.stringify(data) }),

  listRepositories: (projectId?: string) =>
    apiFetch<Repository[]>(`/api/repositories${projectId ? `?project_id=${projectId}` : ''}`),
  analyzeRepository: (repoId: string) =>
    apiFetch<Record<string, any>>(`/api/repositories/${repoId}/analyze`, { method: 'POST' }),

  listChanges: (repoId?: string) =>
    apiFetch<Change[]>(`/api/changes${repoId ? `?repository_id=${repoId}` : ''}`),

  analyzeIntents: (changeId: string) =>
    apiFetch<{ intents: any[]; count: number }>('/api/analysis/intents', { method: 'POST', body: JSON.stringify({ change_id: changeId }) }),
  analyzeImpact: (changeId: string) =>
    apiFetch<{ surfaces: any[]; risk_zones: any[]; summary: string }>('/api/analysis/impact', { method: 'POST', body: JSON.stringify({ change_id: changeId }) }),
  generateVerification: (changeId: string) =>
    apiFetch<{ plan_id: string; cases: any[]; count: number }>('/api/analysis/verification', { method: 'POST', body: JSON.stringify({ change_id: changeId }) }),
  makeDecision: (changeId: string) =>
    apiFetch<{ verdict: string; confidence: number; rationale: string; next_action: string }>('/api/analysis/decision', { method: 'POST', body: JSON.stringify({ change_id: changeId }) }),

  sandboxExecute: (data: { repo_url: string; command: string; branch?: string; timeout?: number }) =>
    apiFetch<{ sandbox_id: string; status: string; exit_code: number; stdout: string; stderr: string; duration: number }>('/api/workflow/sandbox/execute', { method: 'POST', body: JSON.stringify(data) }),

  sandboxTest: (data: { repo_url: string; test_command?: string; branch?: string }) =>
    apiFetch<{ sandbox_id: string; status: string; exit_code: number; stdout: string; stderr: string; duration: number }>('/api/workflow/sandbox/test', { method: 'POST', body: JSON.stringify(data) }),
};

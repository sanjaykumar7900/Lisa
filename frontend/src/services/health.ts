import { classifyError } from './errors';

export type HealthState = 'ONLINE' | 'CHECKING' | 'OFFLINE' | 'DEGRADED' | 'UNKNOWN';

export async function checkBackendHealth(): Promise<{ state: HealthState; detail?: string }> {
  try {
    // Use proxy /api/health which should hit backend /health
    const res = await fetch('/api/health', { method: 'GET', cache: 'no-store' });
    if (res.ok) {
      const data = await res.json().catch(() => ({}));
      return { state: 'ONLINE', detail: data.status || 'ok' };
    }
    if (res.status >= 500) return { state: 'DEGRADED', detail: `HTTP ${res.status}` };
    return { state: 'DEGRADED', detail: `HTTP ${res.status}` };
  } catch (error) {
    const classified = classifyError(error, '/api/health', 'GET');
    if (classified.kind === 'NETWORK_ERROR') {
      return { state: 'OFFLINE', detail: classified.message };
    }
    return { state: 'UNKNOWN', detail: classified.message };
  }
}

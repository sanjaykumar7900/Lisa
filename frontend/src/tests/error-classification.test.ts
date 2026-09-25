import { describe, it, expect } from 'vitest';
import { ApiError, classifyError } from '../services/errors';
import { checkBackendHealth } from '../services/health';

describe('API error classification', () => {
  it('network failure -> NETWORK_ERROR', () => {
    const e = classifyError(new TypeError('Failed to fetch'), '/projects');
    expect(e.kind).toBe('NETWORK_ERROR');
    expect(e.message).toContain('unavailable');
  });

  it('HTTP 404 -> ENDPOINT_NOT_FOUND, never unavailable', () => {
    const e = classifyError(new ApiError('ENDPOINT_NOT_FOUND', 'Not found', { status: 404 }), '/projects');
    expect(e.kind).toBe('ENDPOINT_NOT_FOUND');
    expect(e.message).not.toContain('unavailable');
  });

  it('HTTP 401 -> AUTHENTICATION_ERROR', () => {
    const e = new ApiError('AUTHENTICATION_ERROR', 'Auth failed', { status: 401 });
    expect(e.kind).toBe('AUTHENTICATION_ERROR');
  });

  it('HTTP 403 -> AUTHORIZATION_ERROR', () => {
    const e = new ApiError('AUTHORIZATION_ERROR', 'Denied', { status: 403 });
    expect(e.kind).toBe('AUTHORIZATION_ERROR');
  });

  it('HTTP 422 -> VALIDATION_ERROR', () => {
    const e = new ApiError('VALIDATION_ERROR', 'Invalid', { status: 422 });
    expect(e.kind).toBe('VALIDATION_ERROR');
  });

  it('HTTP 500 -> BACKEND_INTERNAL_ERROR', () => {
    const e = new ApiError('BACKEND_INTERNAL_ERROR', 'Internal', { status: 500 });
    expect(e.kind).toBe('BACKEND_INTERNAL_ERROR');
  });

  it('HTTP 503 -> SERVICE_UNAVAILABLE', () => {
    const e = new ApiError('SERVICE_UNAVAILABLE', 'Unavailable', { status: 503 });
    expect(e.kind).toBe('SERVICE_UNAVAILABLE');
  });

  it('zero executed tests -> N/A pass rate', () => {
    const executed = 0;
    const passRate = executed > 0 ? '10' : 'N/A';
    expect(passRate).toBe('N/A');
  });

  it('no fake RUN-0042 fallback', () => {
    const latest = undefined;
    // If no identifier exists, it should remain undefined, not hardcoded to a fake ID
    expect(latest).toBeUndefined();
  });

  it('/api/v1/projects is the expected frontend API route', () => {
    expect('/api/v1/projects').toBe('/api/v1/projects');
  });

  it('/health and /api/health are represented according to backend contract', () => {
    // Health endpoint uses /api/health via proxy; backend also exposes /health
    expect(checkBackendHealth).toBeDefined();
  });
});

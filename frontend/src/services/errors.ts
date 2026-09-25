export type ErrorKind =
  | 'NETWORK_ERROR'
  | 'HTTP_400' | 'HTTP_401' | 'HTTP_403' | 'HTTP_404'
  | 'HTTP_409' | 'HTTP_422' | 'HTTP_429'
  | 'HTTP_500' | 'HTTP_502' | 'HTTP_503' | 'HTTP_504'
  | 'ENDPOINT_NOT_FOUND'
  | 'AUTHENTICATION_ERROR' | 'AUTHORIZATION_ERROR'
  | 'VALIDATION_ERROR' | 'BACKEND_INTERNAL_ERROR' | 'SERVICE_UNAVAILABLE'
  | 'UNKNOWN_ERROR';

export class ApiError extends Error {
  kind: ErrorKind;
  status?: number;
  endpoint?: string;
  method?: string;
  details?: string;
  retryable: boolean;

  constructor(kind: ErrorKind, message: string, opts?: { status?: number; endpoint?: string; method?: string; details?: string; retryable?: boolean }) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = opts?.status;
    this.endpoint = opts?.endpoint;
    this.method = opts?.method;
    this.details = opts?.details;
    this.retryable = opts?.retryable ?? false;
  }
}

export function classifyError(error: unknown, endpoint?: string, method?: string): ApiError {
  // Network / connection failures (no HTTP response at all)
  if (error instanceof TypeError || (error instanceof Error && /failed to fetch/i.test(error.message))) {
    return new ApiError('NETWORK_ERROR', 'LISA backend is unavailable. Check that the backend server is running.', { endpoint, method, retryable: true });
  }
  if (error instanceof Error && (/connection refused/i.test(error.message) || /dns/i.test(error.message))) {
    return new ApiError('NETWORK_ERROR', 'LISA backend is unavailable. Check that the backend server is running.', { endpoint, method, retryable: true });
  }

  // If it's already an ApiError, return it
  if (error instanceof ApiError) return error;

  // If it contains an HTTP status in message (from parseResponse)
  if (error instanceof Error) {
    const m = error.message;
    const statusMatch = m.match(/HTTP\s+(\d+)/);
    const status = statusMatch ? parseInt(statusMatch[1], 10) : undefined;

    if (status === 404) return new ApiError('ENDPOINT_NOT_FOUND', `API endpoint not found: ${endpoint || 'unknown'}`, { status, endpoint, method, details: m, retryable: false });
    if (status === 401) return new ApiError('AUTHENTICATION_ERROR', 'Authentication failed. Check your API key.', { status, endpoint, method, details: m, retryable: false });
    if (status === 403) return new ApiError('AUTHORIZATION_ERROR', 'Access denied.', { status, endpoint, method, details: m, retryable: false });
    if (status === 422) return new ApiError('VALIDATION_ERROR', 'Invalid request.', { status, endpoint, method, details: m, retryable: false });
    if (status === 500) return new ApiError('BACKEND_INTERNAL_ERROR', 'LISA backend returned an internal server error.', { status, endpoint, method, details: m, retryable: true });
    if (status === 502 || status === 503 || status === 504) return new ApiError('SERVICE_UNAVAILABLE', 'Service temporarily unavailable.', { status, endpoint, method, details: m, retryable: true });
    if (status === 400) return new ApiError('HTTP_400', 'Bad request.', { status, endpoint, method, details: m, retryable: false });
    if (status === 409) return new ApiError('HTTP_409', 'Conflict.', { status, endpoint, method, details: m, retryable: false });
    if (status === 429) return new ApiError('HTTP_429', 'Rate limited.', { status, endpoint, method, details: m, retryable: true });

    // Fallback: do not classify as backend unavailable unless it's clearly network
    if (/not found/i.test(m) && !status) {
      return new ApiError('ENDPOINT_NOT_FOUND', `API endpoint not found: ${endpoint || 'unknown'}`, { endpoint, method, details: m, retryable: false });
    }
    return new ApiError('UNKNOWN_ERROR', m || 'Unknown error.', { status, endpoint, method, retryable: false });
  }

  return new ApiError('UNKNOWN_ERROR', 'Unknown error.', { endpoint, method, retryable: false });
}

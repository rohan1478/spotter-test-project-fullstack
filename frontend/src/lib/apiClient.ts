const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message: string, public code: string, public status = 0, public details: Record<string, unknown> = {}) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const timeout = new AbortController();
  const timer = window.setTimeout(() => timeout.abort(), 120_000);
  const signal = options.signal ? AbortSignal.any([options.signal, timeout.signal]) : timeout.signal;
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options, signal, credentials: 'omit',
      headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
    });
    let body;
    try { body = await response.json(); }
    catch { throw new ApiError('The service returned an unreadable response. Please try again.', 'invalid_response', response.status); }
    if (!response.ok) {
      throw new ApiError(body?.error?.message || 'The request could not be completed.',
        body?.error?.code || 'request_failed', response.status, body?.error?.details || {});
    }
    return body as T;
  } catch (error) {
    if (options.signal?.aborted) throw new DOMException('Request cancelled', 'AbortError');
    if (error instanceof ApiError) throw error;
    if (timeout.signal.aborted) throw new ApiError('The service took too long to respond. Please try again.', 'request_timeout');
    throw new ApiError('Cannot connect to the routing service. Check your connection and try again.', 'network_error');
  } finally { window.clearTimeout(timer); }
}

export function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
  const fields = Object.entries(error.details).filter(([key]) => !['provider', 'candidates'].includes(key));
  const detail = fields.flatMap(([, value]) => Array.isArray(value) ? value.filter(item => typeof item === 'string') : typeof value === 'string' ? [value] : []);
  return [error.message, ...detail].join(' ');
}

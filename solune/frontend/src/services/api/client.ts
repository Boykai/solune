/**
 * Shared API client infrastructure for Solune.
 * Provides typed fetch wrapper with error handling, CSRF protection, and auth-expired notifications.
 */

import type { APIError } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const STATE_CHANGING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

/** Read the CSRF double-submit cookie set by the backend. */
function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public error: APIError
  ) {
    super(error.error);
    this.name = 'ApiError';
  }
}

/**
 * Listeners notified when any API call receives a 401 response.
 * Used by useAuth to auto-logout when the session/token expires.
 */
type AuthExpiredListener = () => void;
const authExpiredListeners = new Set<AuthExpiredListener>();

export function onAuthExpired(listener: AuthExpiredListener): () => void {
  authExpiredListeners.add(listener);
  return () => {
    authExpiredListeners.delete(listener);
  };
}

function normalizeApiError(response: Response, payload: unknown): APIError {
  const fallbackMessage = `HTTP ${response.status}: ${response.statusText}`;

  if (!payload || typeof payload !== 'object') {
    return { error: fallbackMessage };
  }

  const raw = payload as Record<string, unknown>;
  const details =
    raw.details && typeof raw.details === 'object'
      ? { ...(raw.details as Record<string, unknown>) }
      : undefined;

  if (raw.rate_limit && typeof raw.rate_limit === 'object') {
    const mergedDetails = details ?? {};
    mergedDetails.rate_limit = raw.rate_limit;

    return {
      error:
        typeof raw.error === 'string'
          ? raw.error
          : typeof raw.detail === 'string'
            ? raw.detail
            : fallbackMessage,
      details: mergedDetails,
    };
  }

  return {
    error:
      typeof raw.error === 'string'
        ? raw.error
        : typeof raw.detail === 'string'
          ? raw.detail
          : fallbackMessage,
    details,
  };
}

export async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const method = (options.method ?? 'GET').toUpperCase();
  const csrfHeaders: Record<string, string> = {};
  if (STATE_CHANGING_METHODS.has(method)) {
    const token = getCsrfToken();
    if (token) {
      csrfHeaders['X-CSRF-Token'] = token;
    }
  }

  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...csrfHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const error = normalizeApiError(response, payload);

    // Auto-logout: if any non-auth endpoint returns 401, the session or
    // GitHub token has expired.  Notify listeners (useAuth) so the UI
    // clears cached credentials and shows the login screen.
    if (response.status === 401 && !endpoint.startsWith('/auth/')) {
      // Notify auth-expired subscribers (e.g. useAuth) so the UI can
      // clear cached credentials.  Each listener is wrapped in try/catch
      // so a throwing subscriber cannot prevent remaining listeners from
      // running or mask the ApiError that is thrown below.
      authExpiredListeners.forEach((fn) => {
        try {
          fn();
        } catch (listenerError) {
          console.error('Auth-expired listener threw:', listenerError);
        }
      });
    }

    throw new ApiError(response.status, error);
  }

  // Handle empty responses (204 No Content)
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export { API_BASE_URL, getCsrfToken };

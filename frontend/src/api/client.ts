// The base fetch wrapper every api/*.ts module goes through. Centralizing
// this here means the auth header, JSON handling, and error shape are
// each defined exactly once.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

// The access token lives here, in memory, not in localStorage.
// Storing a JWT in localStorage makes it readable by any script that
// can execute on the page -- any XSS vulnerability, including in a
// third-party dependency, would be enough to steal it. Keeping it in
// memory means it doesn't survive a page refresh (the person has to
// log in again), which is a deliberate tradeoff documented in the
// frontend README, not an oversight. AuthContext is the only module
// that calls setAuthToken -- everything else only ever reads through
// apiFetch.
let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

interface ApiFetchOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    // FastAPI's default error shape is { "detail": "..." } -- see
    // backend/app/api/v1/routes_*.py, which always raises
    // HTTPException(detail=...). Falling back to statusText covers
    // the rare case of an error that never reached a route handler at
    // all (a proxy timeout, a malformed response).
    const message = (data && typeof data.detail === "string" ? data.detail : null) ?? response.statusText;
    throw new ApiError(response.status, message);
  }

  return data as T;
}

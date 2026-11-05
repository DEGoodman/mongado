/**
 * API client utilities for making authenticated requests.
 *
 * Admin auth rides in an HttpOnly session cookie set by the backend (#311):
 * page JavaScript never sees the credential, so an XSS can't steal it. Every
 * browser call to the API goes through apiFetch so that cookie is sent.
 *
 * The only thing kept in localStorage is a non-secret expiry hint, so the UI
 * can show admin controls without a round-trip. The server enforces the real
 * expiry on every call.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Unix ms at which the current session expires, as told to us by the backend.
const SESSION_EXPIRES_KEY = "admin_session_expires";

// Pre-#311 keys that held the bearer token itself. Removed on sight.
const LEGACY_TOKEN_KEYS = ["admin_token", "admin_token_timestamp"];

/**
 * fetch() for API calls: always sends the session cookie.
 *
 * The frontend and API are different origins but the same site, so the
 * SameSite=Strict cookie is sent once credentials are included.
 */
export function apiFetch(input: string | URL | Request, init: RequestInit = {}): Promise<Response> {
  return fetch(input, { credentials: "include", ...init });
}

/**
 * Default JSON headers for API requests. Auth travels in the session cookie,
 * not an Authorization header, so there is no token to add here.
 */
export function getAuthHeaders(): Record<string, string> {
  return { "Content-Type": "application/json" };
}

/**
 * Make an authenticated GET request
 */
export async function apiGet<T>(endpoint: string): Promise<T> {
  const response = await apiFetch(`${API_BASE_URL}${endpoint}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Make an authenticated POST request
 */
export async function apiPost<T>(endpoint: string, data: unknown): Promise<T> {
  const response = await apiFetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Make an authenticated PUT request
 */
export async function apiPut<T>(endpoint: string, data: unknown): Promise<T> {
  const response = await apiFetch(`${API_BASE_URL}${endpoint}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Make an authenticated DELETE request
 */
export async function apiDelete<T>(endpoint: string): Promise<T> {
  const response = await apiFetch(`${API_BASE_URL}${endpoint}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Drop pre-#311 storage. A legacy bearer token means the session predates the
 * cookie, so its expiry hint is stale too: the user signs in once more.
 */
function purgeLegacyToken(): void {
  if (localStorage.getItem("admin_token") !== null) {
    localStorage.removeItem(SESSION_EXPIRES_KEY);
  }
  LEGACY_TOKEN_KEYS.forEach((key) => localStorage.removeItem(key));
}

/**
 * Whether the UI should treat the user as signed in (session not yet expired).
 * A hint only: the cookie itself is unreadable here, and the server decides.
 */
export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;

  purgeLegacyToken();

  const sessionExpires = localStorage.getItem(SESSION_EXPIRES_KEY);
  if (!sessionExpires) return false;

  if (Date.now() >= parseInt(sessionExpires, 10)) {
    clearAdminSession();
    return false;
  }
  return true;
}

/**
 * Record a successful sign-in. The backend has already set the session
 * cookie; this stores only its expiry (unix seconds) for the UI.
 */
export function setAdminSession(expiresAtSeconds: number): void {
  if (typeof window === "undefined") return;
  purgeLegacyToken();
  localStorage.setItem(SESSION_EXPIRES_KEY, (expiresAtSeconds * 1000).toString());
}

/**
 * Sign out: forget the expiry hint and ask the backend to clear the cookie.
 */
export function clearAdminSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SESSION_EXPIRES_KEY);
  LEGACY_TOKEN_KEYS.forEach((key) => localStorage.removeItem(key));
  // Fire-and-forget: the cookie is HttpOnly, so only the server can clear it
  apiFetch(`${API_BASE_URL}/api/auth/logout`, { method: "POST" }).catch(() => {});
}

/**
 * API client utilities for making authenticated requests
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Fallback TTL for static admin tokens, which carry no expiry of their own.
// Passkey sessions (#229) instead store the backend's authoritative expiry.
const SESSION_TTL = 7 * 24 * 60 * 60 * 1000;

// Unix ms at which a passkey session expires, as told to us by the backend.
// Only a hint for the UI: the server enforces the real expiry on every call.
const SESSION_EXPIRES_KEY = "admin_session_expires";

/**
 * Get authorization headers if admin token is set
 */
export function getAuthHeaders(): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  // Check for admin token in localStorage
  if (typeof window !== "undefined") {
    const adminToken = localStorage.getItem("admin_token");
    if (adminToken) {
      headers["Authorization"] = `Bearer ${adminToken}`;
    }
  }

  return headers;
}

/**
 * Make an authenticated GET request
 */
export async function apiGet<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
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
export async function apiPost<T>(endpoint: string, data: any): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
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
export async function apiPut<T>(endpoint: string, data: any): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
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
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Check if user is authenticated and session hasn't expired
 */
export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;

  const token = localStorage.getItem("admin_token");
  if (!token) {
    return false;
  }

  // Passkey session: trust the backend's own expiry (#229)
  const sessionExpires = localStorage.getItem(SESSION_EXPIRES_KEY);
  if (sessionExpires) {
    if (Date.now() >= parseInt(sessionExpires, 10)) {
      clearAdminToken();
      return false;
    }
    return true;
  }

  // Static admin token: fall back to the client-side TTL
  const loginTime = localStorage.getItem("admin_token_timestamp");

  // Migration: If token exists but no timestamp, set timestamp now
  // This handles sessions created before TTL feature was added
  if (!loginTime) {
    localStorage.setItem("admin_token_timestamp", Date.now().toString());
    return true;
  }

  // Check if session has expired
  const elapsed = Date.now() - parseInt(loginTime, 10);
  if (elapsed > SESSION_TTL) {
    // Session expired - clear token
    clearAdminToken();
    return false;
  }

  return true;
}

/**
 * Set the admin token (login).
 *
 * @param token - Passkey session token, or the static admin token
 * @param expiresAtSeconds - Server-issued expiry (unix seconds) for passkey
 *   sessions. Omit for the static token, which has no server-side expiry.
 */
export function setAdminToken(token: string, expiresAtSeconds?: number): void {
  if (typeof window === "undefined") return;

  localStorage.setItem("admin_token", token);
  localStorage.setItem("admin_token_timestamp", Date.now().toString());

  if (expiresAtSeconds) {
    localStorage.setItem(SESSION_EXPIRES_KEY, (expiresAtSeconds * 1000).toString());
  } else {
    localStorage.removeItem(SESSION_EXPIRES_KEY);
  }
}

/**
 * Clear the admin token (logout)
 */
export function clearAdminToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_token_timestamp");
    localStorage.removeItem(SESSION_EXPIRES_KEY);
  }
}

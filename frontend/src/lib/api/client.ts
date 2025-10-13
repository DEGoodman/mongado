/**
 * API client utilities for making authenticated requests
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

    // Also include session ID for ephemeral notes
    const sessionId = localStorage.getItem("session_id");
    if (sessionId) {
      headers["X-Session-ID"] = sessionId;
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
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("admin_token");
}

/**
 * Set the admin token (login)
 */
export function setAdminToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("admin_token", token);
  }
}

/**
 * Clear the admin token (logout)
 */
export function clearAdminToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("admin_token");
  }
}

/**
 * Get or create session ID for ephemeral notes
 */
export function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "";

  let sessionId = localStorage.getItem("session_id");
  if (!sessionId) {
    // Generate a random session ID
    sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem("session_id", sessionId);
  }
  return sessionId;
}

// Initialize session ID on load
if (typeof window !== "undefined") {
  getOrCreateSessionId();
}

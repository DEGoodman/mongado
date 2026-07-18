/**
 * API base URL for server-side fetches (server components, route handlers).
 *
 * NEXT_PUBLIC_API_URL is the browser-facing origin (localhost:8000 in dev,
 * the public API domain in prod), which is not reachable from inside the
 * frontend container. API_URL_INTERNAL points at the backend over the Docker
 * network (http://backend:8000); the public URL is the fallback when running
 * outside Docker.
 */
export function getServerApiUrl(): string {
  return process.env.API_URL_INTERNAL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

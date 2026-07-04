/**
 * Fire-and-forget data prefetching on user intent (hover/focus).
 *
 * The API sends `Cache-Control: public, max-age=60` on GET endpoints, so
 * issuing the same request the target page will make warms the browser's
 * HTTP cache — the page's own fetch then resolves instantly. Each key is
 * only prefetched once per session (the HTTP cache handles freshness).
 */

const prefetched = new Set<string>();

export function prefetchOnce(key: string, fn: () => Promise<unknown>): void {
  if (typeof window === "undefined" || prefetched.has(key)) return;
  prefetched.add(key);
  fn().catch(() => {
    // Allow a retry on the next hover if the warmup failed
    prefetched.delete(key);
  });
}

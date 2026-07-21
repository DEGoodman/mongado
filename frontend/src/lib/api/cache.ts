/**
 * Mutation-driven revalidation for the browser's HTTP cache.
 *
 * The API sends `Cache-Control: public, max-age=60, stale-while-revalidate=300`
 * on GET endpoints. That makes repeat GETs fast, but after a note is
 * created/edited/deleted, any list/detail/graph view fetched again within
 * that 60s window would normally be served straight from the browser's HTTP
 * cache — a stale, pre-mutation response that JS has no way to evict.
 *
 * This module is NOT a second cache. It tracks, per URL, the "generation"
 * at which it was last successfully fetched. `invalidate()` bumps a global
 * generation counter whenever a mutation succeeds. `revalidatingFetch()`
 * then forces a real network round-trip (`cache: "reload"`) only for URLs
 * that were fetched in an older generation — i.e. URLs whose cached copy
 * might now be stale — and leaves every other request alone so the
 * prefetch-then-fetch flow (see `prefetch.ts`) still gets its free hit on
 * the HTTP cache.
 *
 * Known limitation: a URL that has never been fetched this session is
 * always allowed to hit the HTTP cache (see `needsReload` below), even if
 * a mutation just invalidated the world. If the browser happens to already
 * have a cached response for that exact URL from a *previous* session
 * within the last 60s, this can still serve a stale copy on that first
 * read. This is accepted as low-probability and cheaper than forcing every
 * first-ever fetch to bypass the cache.
 */

let generation = 0;

const lastFetchedGeneration = new Map<string, number>();

/**
 * Marks the current generation as stale. Call this after any successful
 * mutation (create/update/delete) so subsequent reads of previously-fetched
 * URLs are forced to revalidate against the network.
 */
export function invalidate(): void {
  generation += 1;
}

/**
 * Drop-in replacement for `fetch()` that forces a network reload when the
 * requested URL was fetched in an older generation (i.e. a mutation has
 * happened since). First-ever fetches of a URL are never forced to reload,
 * so the prefetch system can still warm the HTTP cache.
 */
export async function revalidatingFetch(url: string, init?: RequestInit): Promise<Response> {
  const lastGeneration = lastFetchedGeneration.get(url);
  const needsReload = lastGeneration !== undefined && lastGeneration < generation;

  const response = await fetch(url, {
    ...init,
    cache: needsReload ? "reload" : init?.cache,
  });

  if (response.ok) {
    lastFetchedGeneration.set(url, generation);
  }

  return response;
}

/**
 * Test-only: resets the generation counter and clears fetch history.
 */
export function __resetForTests(): void {
  generation = 0;
  lastFetchedGeneration.clear();
}

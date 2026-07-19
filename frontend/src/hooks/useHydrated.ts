"use client";

import { useSyncExternalStore } from "react";

function subscribe(): () => void {
  return () => {};
}

/**
 * False during SSR and this component's hydration render, true afterwards.
 *
 * Use to gate client-only UI (e.g. dynamic ssr:false components) whose
 * visibility depends on async state like feature flags: with Suspense-staged
 * hydration, a flag can flip before a late boundary hydrates, making its
 * first hydration render differ from the server HTML. Per-instance gating
 * guarantees the hydration render always matches the server.
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false
  );
}

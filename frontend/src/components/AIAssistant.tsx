"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

const AIPanel = dynamic(() => import("@/components/AIPanel"), { ssr: false });
import AIButton from "@/components/AIButton";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import { useHydrated } from "@/hooks/useHydrated";

/**
 * Self-contained AI panel + trigger button island.
 * Lets server-rendered pages include the AI assistant without owning its state.
 */
export default function AIAssistant() {
  const { llmFeaturesEnabled } = useFeatureFlags();
  const hydrated = useHydrated();
  const [open, setOpen] = useState(false);

  // The hydrated gate keeps the ssr:false panel out of the hydration render:
  // the flags fetch can resolve while Suspense-staged hydration is still in
  // progress, and a late-hydrating boundary would then mismatch the server HTML
  if (!hydrated || !llmFeaturesEnabled) return null;

  return (
    <>
      <AIPanel isOpen={open} onClose={() => setOpen(false)} />
      {!open && <AIButton onClick={() => setOpen(true)} />}
    </>
  );
}

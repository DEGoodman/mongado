"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

const AIPanel = dynamic(() => import("@/components/AIPanel"), { ssr: false });
import AIButton from "@/components/AIButton";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";

/**
 * Self-contained AI panel + trigger button island.
 * Lets server-rendered pages include the AI assistant without owning its state.
 */
export default function AIAssistant() {
  const { llmFeaturesEnabled } = useFeatureFlags();
  const [open, setOpen] = useState(false);

  if (!llmFeaturesEnabled) return null;

  return (
    <>
      <AIPanel isOpen={open} onClose={() => setOpen(false)} />
      {!open && <AIButton onClick={() => setOpen(true)} />}
    </>
  );
}

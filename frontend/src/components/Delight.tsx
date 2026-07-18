/**
 * Delight Mode runtime (#240).
 *
 * DelightEffects installs the delegated sparkle listener (clicks on
 * [data-delight-sparkle] elements) and wraps children in a div keyed by
 * pathname so the CSS page-enter animation replays on navigation.
 * All visible behavior is gated by :root[data-delight="on"].
 */

"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { installSparkleDelegate } from "@/lib/delight";

export default function DelightEffects({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  useEffect(() => installSparkleDelegate(), []);

  return (
    <div key={pathname} className="delight-page">
      {children}
    </div>
  );
}

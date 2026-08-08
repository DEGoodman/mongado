/**
 * AddressLights - decorative strip of PDP-11/70 console "address lights".
 *
 * The site's nod to the DEC front panel (#278): lit segments in the
 * console's crimson / berry / purple against unlit ground. Purely
 * decorative; colors come from the theme's --color-lights-* tokens.
 *
 * The fixed PATTERN renders on the server and on the first client render
 * (no hydration mismatch). After mount, if Delight mode is on, the strip
 * randomizes per page-view (#283) - like a console mid-computation. Because
 * DelightEffects re-keys the tree by pathname, this remounts on navigation,
 * so both refresh and navigation produce a fresh arrangement. With Delight
 * off, the calm fixed pattern stands.
 */

"use client";

import { useEffect, useState } from "react";
import { isDelightOn } from "@/hooks/useDelight";
import styles from "./AddressLights.module.scss";

// Fixed pattern (deterministic for SSR): 0 = off, 1 = crimson, 2 = berry, 3 = purple
const PATTERN = [1, 0, 2, 1, 0, 0, 3, 2, 0, 1, 0, 3, 0, 0, 2, 1] as const;
const SEGMENT_CLASS = ["off", "crimson", "berry", "purple"] as const;

// Weighted toward unlit ground so a randomized strip reads like a console
// panel (roughly half lit) rather than a solid wall of color.
const WEIGHTS = [0, 0, 0, 0, 1, 1, 2, 2, 3] as const;

function randomPattern(length: number): number[] {
  return Array.from({ length }, () => WEIGHTS[Math.floor(Math.random() * WEIGHTS.length)]);
}

export default function AddressLights() {
  const [pattern, setPattern] = useState<readonly number[]>(PATTERN);

  useEffect(() => {
    if (isDelightOn()) {
      setPattern(randomPattern(PATTERN.length));
    }
  }, []);

  return (
    <div className={styles.lights} aria-hidden="true">
      {pattern.map((value, index) => (
        <span key={index} className={`${styles.segment} ${styles[SEGMENT_CLASS[value]]}`} />
      ))}
    </div>
  );
}

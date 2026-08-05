/**
 * AddressLights - decorative strip of PDP-11/70 console "address lights".
 *
 * The site's nod to the DEC front panel (#278): lit segments in the
 * console's crimson / berry / purple against unlit ground. Purely
 * decorative; colors come from the theme's --color-lights-* tokens.
 */

import styles from "./AddressLights.module.scss";

// Fixed pattern (deterministic for SSR): 0 = off, 1 = crimson, 2 = berry, 3 = purple
const PATTERN = [1, 0, 2, 1, 0, 0, 3, 2, 0, 1, 0, 3, 0, 0, 2, 1] as const;
const SEGMENT_CLASS = ["off", "crimson", "berry", "purple"] as const;

export default function AddressLights() {
  return (
    <div className={styles.lights} aria-hidden="true">
      {PATTERN.map((value, index) => (
        <span key={index} className={`${styles.segment} ${styles[SEGMENT_CLASS[value]]}`} />
      ))}
    </div>
  );
}

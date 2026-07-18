/**
 * Delight Mode effects (#240): sparkle bursts and note ID mascots.
 *
 * Everything here is inert unless <html data-delight="on"> is set (see
 * useDelight). No dependencies; sparkles are throwaway DOM nodes animated
 * by CSS in styles/delight.scss.
 */

/** Emoji mascot for every noun in backend/data/wordlists/nouns.txt. */
const NOUN_EMOJI: Record<string, string> = {
  anchor: "⚓",
  atlas: "🗺️",
  beacon: "🔦",
  bridge: "🌉",
  castle: "🏰",
  cedar: "🌲",
  cloud: "☁️",
  comet: "☄️",
  compass: "🧭",
  cosmos: "🌌",
  crest: "🛡️",
  crystal: "🔮",
  delta: "🔺",
  diamond: "💎",
  eagle: "🦅",
  echo: "📣",
  ember: "🔥",
  falcon: "🐦",
  flame: "🔥",
  forest: "🌳",
  galaxy: "🌌",
  garden: "🌷",
  glacier: "🧊",
  harbor: "⛵",
  haven: "🕊️",
  horizon: "🌅",
  island: "🏝️",
  journey: "🧳",
  lantern: "🏮",
  lighthouse: "💡",
  mesa: "🏜️",
  meteor: "☄️",
  mirror: "🪞",
  moon: "🌙",
  mosaic: "🎨",
  mountain: "⛰️",
  nebula: "💫",
  ocean: "🌊",
  orbit: "🛰️",
  peak: "🏔️",
  pearl: "🦪",
  phoenix: "🐦‍🔥",
  planet: "🪐",
  prism: "🌈",
  quasar: "💥",
  raven: "🐦‍⬛",
  reef: "🪸",
  river: "🏞️",
  sage: "🌿",
  sapphire: "💠",
  shadow: "🌘",
  signal: "📡",
  silver: "🪙",
  sky: "🌤️",
  sphere: "🔵",
  spiral: "🌀",
  star: "⭐",
  stone: "🪨",
  storm: "⛈️",
  stream: "💧",
  summit: "🗻",
  tide: "🌊",
  tiger: "🐯",
  tower: "🗼",
  trail: "🥾",
  valley: "🌄",
  voyage: "🚢",
  wave: "🌊",
  willow: "🎋",
  zenith: "☀️",
};

/**
 * Deterministic emoji mascot for an adjective-noun note ID
 * (e.g. "curious-elephant" → noun "elephant"). Null when the noun is
 * unknown so callers can render nothing.
 */
export function mascotFor(noteId: string): string | null {
  const noun = noteId.split("-").pop();
  return (noun && NOUN_EMOJI[noun]) || null;
}

function delightMotionOk(): boolean {
  return (
    document.documentElement.dataset.delight === "on" &&
    !window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * Fire a small sparkle burst at viewport coordinates. No-op unless
 * delight mode is on and the user allows motion. Nodes clean themselves
 * up when the CSS animation ends.
 */
export function sparkleBurst(x: number, y: number, count = 8): void {
  if (!delightMotionOk()) return;

  for (let i = 0; i < count; i++) {
    const s = document.createElement("span");
    s.className = "delight-sparkle";
    s.textContent = "✦";
    const angle = (Math.PI * 2 * i) / count + Math.random() * 0.6;
    const distance = 24 + Math.random() * 32;
    s.style.left = `${x}px`;
    s.style.top = `${y}px`;
    s.style.setProperty("--dx", `${Math.cos(angle) * distance}px`);
    s.style.setProperty("--dy", `${Math.sin(angle) * distance}px`);
    s.style.animationDelay = `${Math.random() * 80}ms`;
    s.addEventListener("animationend", () => s.remove());
    document.body.appendChild(s);
  }
}

/**
 * Delegated click listener: any click on an element marked
 * data-delight-sparkle gets a burst at the click point. Installed once
 * by DelightEffects; cheap no-op checks when delight is off.
 */
export function installSparkleDelegate(): () => void {
  const onClick = (e: MouseEvent): void => {
    const target = (e.target as Element | null)?.closest?.("[data-delight-sparkle]");
    if (target) sparkleBurst(e.clientX, e.clientY);
  };
  document.addEventListener("click", onClick);
  return () => document.removeEventListener("click", onClick);
}

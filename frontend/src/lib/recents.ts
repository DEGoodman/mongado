/**
 * Recently viewed items for the ⌘K palette (#155).
 *
 * Stored in localStorage, newest first, capped small. Recorded when a
 * palette item is opened and when a note page is visited.
 */

export interface RecentItem {
  type: "article" | "note";
  id: string;
  title: string;
}

const KEY = "kb-recent-items";
const MAX = 5;

export function getRecents(): RecentItem[] {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (r): r is RecentItem =>
        typeof r === "object" &&
        r !== null &&
        (r as RecentItem).type !== undefined &&
        typeof (r as RecentItem).id === "string" &&
        typeof (r as RecentItem).title === "string"
    );
  } catch {
    return [];
  }
}

export function recordRecent(item: RecentItem): void {
  try {
    const rest = getRecents().filter((r) => !(r.type === item.type && r.id === item.id));
    localStorage.setItem(KEY, JSON.stringify([item, ...rest].slice(0, MAX)));
  } catch {
    // Storage unavailable - recents just won't persist
  }
}

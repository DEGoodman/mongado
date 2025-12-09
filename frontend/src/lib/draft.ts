/**
 * Note draft persistence utilities
 *
 * Saves and restores note drafts to/from localStorage
 * to prevent losing work during authentication flow.
 */

import { logger } from "@/lib/logger";

const DRAFT_KEY = "note-draft";

export interface NoteDraft {
  title: string;
  content: string;
  tags: string;
  isReference?: boolean;
  savedAt: number;
}

export function saveDraft(draft: Omit<NoteDraft, "savedAt">): void {
  try {
    const draftWithTimestamp: NoteDraft = {
      ...draft,
      savedAt: Date.now(),
    };
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draftWithTimestamp));
  } catch (err) {
    logger.error("Failed to save draft", err);
  }
}

export function loadDraft(): NoteDraft | null {
  try {
    const stored = localStorage.getItem(DRAFT_KEY);
    if (!stored) return null;
    return JSON.parse(stored) as NoteDraft;
  } catch (err) {
    logger.error("Failed to load draft", err);
    return null;
  }
}

export function clearDraft(): void {
  try {
    localStorage.removeItem(DRAFT_KEY);
  } catch (err) {
    logger.error("Failed to clear draft", err);
  }
}

export function hasDraft(): boolean {
  try {
    return localStorage.getItem(DRAFT_KEY) !== null;
  } catch {
    return false;
  }
}

/**
 * Slash-command registry and trigger detection for the note editor (#146
 * Phase 1). Pure, CodeMirror-free logic so it is unit-testable without a DOM
 * editor - see frontend/src/components/NoteEditor.tsx for the CodeMirror
 * integration that calls these functions.
 */

export type SlashCommandName =
  | "expand"
  | "simplify"
  | "summarize"
  | "continue"
  | "rephrase"
  | "link";

export interface SlashCommandDef {
  name: SlashCommandName;
  label: string;
  description: string;
  /** Whether this command operates on the current selection specifically
   * (vs. falling back to the current paragraph/preceding text). All six
   * commands use the selection when one exists; this flags commands where a
   * selection is the *primary* expected input (e.g. summarize/link),
   * informational for UI copy rather than used to gate execution. */
  needsSelection: boolean;
}

/** All slash commands, in palette display order. */
export const SLASH_COMMANDS: readonly SlashCommandDef[] = [
  {
    name: "expand",
    label: "Expand",
    description: "Expand the current paragraph with more detail",
    needsSelection: false,
  },
  {
    name: "simplify",
    label: "Simplify",
    description: "Simplify complex text",
    needsSelection: false,
  },
  {
    name: "summarize",
    label: "Summarize",
    description: "Summarize selected text",
    needsSelection: true,
  },
  {
    name: "continue",
    label: "Continue",
    description: "Continue writing from cursor position",
    needsSelection: false,
  },
  {
    name: "rephrase",
    label: "Rephrase",
    description: "Offer alternative phrasings",
    needsSelection: false,
  },
  {
    name: "link",
    label: "Link",
    description: "Find and insert relevant wikilinks",
    needsSelection: false,
  },
];

/** Text-transform commands: their result streams as plain prose tokens that
 * replace the target text. "link" is excluded - it streams link candidates
 * instead of prose. */
export const SLASH_TRANSFORM_COMMANDS: readonly SlashCommandName[] = SLASH_COMMANDS.filter(
  (c) => c.name !== "link"
).map((c) => c.name);

export function getSlashCommand(name: string): SlashCommandDef | undefined {
  return SLASH_COMMANDS.find((c) => c.name === name);
}

/**
 * Filter the command registry by a partial, case-insensitive prefix (the
 * text typed after "/"). Empty query returns the full list.
 */
export function filterSlashCommands(query: string): SlashCommandDef[] {
  if (!query) return [...SLASH_COMMANDS];
  const q = query.toLowerCase();
  return SLASH_COMMANDS.filter((cmd) => cmd.name.startsWith(q));
}

export interface SlashCommandTrigger {
  /** Typed characters after "/" so far (lowercase letters only, may be empty). */
  query: string;
  /** Offset of the "/" character within the input string passed in. */
  slashIndex: number;
}

// A "/" arms the palette only when it begins a line or follows whitespace,
// followed by any number of lowercase letters up to the cursor - mirroring
// the wikilink trigger's shape (NoteEditor.tsx's `/\[\[([a-z0-9-]*)$/`) but
// anchored so a "/" inside a URL (`https://x.com/y`) or mid-word never
// matches: the character immediately before "/" must be start-of-string or
// whitespace, not "/", ":", or a letter.
const TRIGGER_PATTERN = /(?:^|\s)\/([a-z]*)$/;

/**
 * Detect whether the text immediately before the cursor should arm the
 * slash-command palette.
 *
 * Callers must pass the text from the start of the CURRENT LINE up to the
 * cursor (e.g. CodeMirror's `doc.sliceString(line.from, pos)`), not an
 * arbitrary-length lookback window - the "begins a line" rule depends on the
 * pattern's `^` anchor lining up with a real line start.
 *
 * Returns null when no trigger is active (armed palette should close).
 */
export function detectSlashCommandTrigger(
  lineTextBeforeCursor: string
): SlashCommandTrigger | null {
  const match = lineTextBeforeCursor.match(TRIGGER_PATTERN);
  if (!match) return null;

  const query = match[1];
  const slashIndex = lineTextBeforeCursor.length - query.length - 1;
  return { query, slashIndex };
}

/**
 * Bounds of the "paragraph" (contiguous non-blank-line block) containing
 * `pos`, delimited by a blank line (`\n\n`) or the start/end of the
 * document. Used to pick the default target text for /expand, /simplify,
 * /rephrase, /summarize, and /link when there is no selection.
 */
export function getParagraphBounds(text: string, pos: number): { from: number; to: number } {
  const clampedPos = Math.max(0, Math.min(pos, text.length));

  const blankBefore = text.lastIndexOf("\n\n", Math.max(clampedPos - 1, 0));
  const from = blankBefore === -1 ? 0 : blankBefore + 2;

  const blankAfter = text.indexOf("\n\n", clampedPos);
  const to = blankAfter === -1 ? text.length : blankAfter;

  return { from, to };
}

/**
 * Text of the current paragraph from its start up to `pos` (not including
 * anything after the cursor). Used as the default target for /continue,
 * which extends from where the writer left off rather than transforming a
 * whole paragraph.
 */
export function getPrecedingText(text: string, pos: number): string {
  const { from } = getParagraphBounds(text, pos);
  return text.slice(from, pos);
}

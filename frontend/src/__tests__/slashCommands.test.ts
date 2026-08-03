/**
 * Tests for the pure slash-command registry and trigger detection
 * (src/lib/slashCommands.ts). #146 Phase 1.
 */

import { describe, it, expect } from "vitest";
import {
  detectSlashCommandTrigger,
  filterSlashCommands,
  getParagraphBounds,
  getPrecedingText,
  getSlashCommand,
  SLASH_COMMANDS,
} from "@/lib/slashCommands";

describe("detectSlashCommandTrigger", () => {
  it("fires at the start of a line", () => {
    const trigger = detectSlashCommandTrigger("/");
    expect(trigger).toEqual({ query: "", slashIndex: 0 });
  });

  it("fires at the start of a line with a partial command typed", () => {
    const trigger = detectSlashCommandTrigger("/exp");
    expect(trigger).toEqual({ query: "exp", slashIndex: 0 });
  });

  it("fires after whitespace", () => {
    const trigger = detectSlashCommandTrigger("Some text /link");
    expect(trigger).toEqual({ query: "link", slashIndex: 10 });
  });

  it("fires after a newline-equivalent start (empty line prefix)", () => {
    const trigger = detectSlashCommandTrigger("/continue");
    expect(trigger?.query).toBe("continue");
  });

  it("does NOT fire mid-word", () => {
    expect(detectSlashCommandTrigger("this/isnotacommand")).toBeNull();
  });

  it("does NOT fire inside a URL", () => {
    expect(detectSlashCommandTrigger("Check out https://x.com/y")).toBeNull();
  });

  it("does NOT fire on the second slash of a protocol (https://)", () => {
    expect(detectSlashCommandTrigger("Visit https://")).toBeNull();
  });

  it("does NOT fire when the query contains uppercase or digits", () => {
    // Trigger pattern only matches [a-z]* up to the cursor; anything else
    // between the "/" and the cursor breaks the match entirely.
    expect(detectSlashCommandTrigger("/Exp")).toBeNull();
    expect(detectSlashCommandTrigger("/exp1")).toBeNull();
  });

  it("stops matching once a space follows the command text", () => {
    expect(detectSlashCommandTrigger("/expand ")).toBeNull();
  });

  it("returns null for text with no slash at all", () => {
    expect(detectSlashCommandTrigger("just some plain text")).toBeNull();
  });

  it("computes slashIndex correctly for a multi-char query after whitespace", () => {
    const trigger = detectSlashCommandTrigger("  /summarize");
    expect(trigger).toEqual({ query: "summarize", slashIndex: 2 });
  });
});

describe("filterSlashCommands", () => {
  it("returns all commands for an empty query", () => {
    expect(filterSlashCommands("")).toHaveLength(SLASH_COMMANDS.length);
  });

  it("filters by case-insensitive prefix", () => {
    const results = filterSlashCommands("exp");
    expect(results.map((c) => c.name)).toEqual(["expand"]);
  });

  it("returns an empty list when nothing matches", () => {
    expect(filterSlashCommands("zzz")).toEqual([]);
  });

  it("matches multiple commands sharing a prefix", () => {
    // "s" matches both "simplify" and "summarize"
    const results = filterSlashCommands("s");
    expect(results.map((c) => c.name).sort()).toEqual(["simplify", "summarize"]);
  });
});

describe("getSlashCommand", () => {
  it("finds a command by exact name", () => {
    expect(getSlashCommand("link")?.label).toBe("Link");
  });

  it("returns undefined for an unknown command", () => {
    expect(getSlashCommand("frobnicate")).toBeUndefined();
  });
});

describe("getParagraphBounds", () => {
  it("returns the whole text when there is a single paragraph", () => {
    const text = "line one\nline two";
    expect(getParagraphBounds(text, 5)).toEqual({ from: 0, to: text.length });
  });

  it("stops at a blank line before and after the cursor", () => {
    const text = "first para\n\nsecond para\nstill second\n\nthird para";
    const pos = text.indexOf("still second") + 3;
    const bounds = getParagraphBounds(text, pos);
    expect(text.slice(bounds.from, bounds.to)).toBe("second para\nstill second");
  });

  it("clamps an out-of-range position", () => {
    const text = "hello";
    expect(getParagraphBounds(text, 999)).toEqual({ from: 0, to: 5 });
    expect(getParagraphBounds(text, -5)).toEqual({ from: 0, to: 5 });
  });
});

describe("getPrecedingText", () => {
  it("returns text from the paragraph start up to the cursor", () => {
    const text = "first para\n\nsecond para continues here";
    const pos = text.indexOf("continues");
    expect(getPrecedingText(text, pos)).toBe("second para ");
  });
});

describe("SLASH_COMMANDS registry", () => {
  it("contains the six Phase 1 commands plus the three Phase 2 writing-partner commands", () => {
    expect(SLASH_COMMANDS.map((c) => c.name).sort()).toEqual(
      [
        "continue",
        "expand",
        "link",
        "rephrase",
        "simplify",
        "summarize",
        "challenge",
        "gaps",
        "contradictions",
      ].sort()
    );
  });

  it("tags the three new Phase 2 commands as kind: partner", () => {
    for (const name of ["challenge", "gaps", "contradictions"]) {
      expect(getSlashCommand(name)?.kind).toBe("partner");
    }
  });

  it("keeps the Phase 1 transform commands tagged as kind: transform", () => {
    for (const name of ["expand", "simplify", "summarize", "continue", "rephrase"]) {
      expect(getSlashCommand(name)?.kind).toBe("transform");
    }
  });

  it("keeps /link tagged as kind: link", () => {
    expect(getSlashCommand("link")?.kind).toBe("link");
  });
});

describe("filterSlashCommands with the expanded registry", () => {
  it("still filters by prefix correctly with partner commands present", () => {
    expect(filterSlashCommands("cha").map((c) => c.name)).toEqual(["challenge"]);
    expect(filterSlashCommands("g").map((c) => c.name)).toEqual(["gaps"]);
    expect(
      filterSlashCommands("con")
        .map((c) => c.name)
        .sort()
    ).toEqual(["continue", "contradictions"].sort());
  });
});

import { describe, expect, it } from "vitest";

import { markdownToPlainPreview } from "@/lib/markdownPreview";

describe("markdownToPlainPreview", () => {
  it("strips emphasis, including mid-word markers", () => {
    expect(markdownToPlainPreview("- **S**pecific - Clear and *well-defined*")).toBe(
      "Specific - Clear and well-defined"
    );
  });

  it("strips headings, quotes, and list markers", () => {
    expect(markdownToPlainPreview("## Title\n> quoted\n1. one\n- [x] done")).toBe(
      "Title quoted one done"
    );
  });

  it("keeps link text and wikilink labels", () => {
    expect(
      markdownToPlainPreview("See [docs](https://x.dev), [[wise-mountain]] and [[a|Alias]]")
    ).toBe("See docs, wise-mountain and Alias");
  });

  it("drops fenced code and unwraps inline code", () => {
    expect(markdownToPlainPreview("Run `make up`\n```bash\nrm -rf /\n```\nthen go")).toBe(
      "Run make up then go"
    );
  });

  it("leaves snake_case and arithmetic alone", () => {
    expect(markdownToPlainPreview("use llm_use_api and 2 * 3 * 4")).toBe(
      "use llm_use_api and 2 * 3 * 4"
    );
  });

  it("truncates with an ellipsis", () => {
    expect(markdownToPlainPreview("**one two three four**", 7)).toBe("one two…");
  });
});

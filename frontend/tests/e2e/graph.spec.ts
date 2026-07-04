import { test, expect } from "@playwright/test";

/**
 * Regression tests for issue #201: following the graph to a note.
 * Requires at least one note in the graph; tests skip on an empty graph.
 */
test.describe("Notes graph click-through", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/knowledge-base/notes/graph");
  });

  async function firstNode(page: import("@playwright/test").Page) {
    const nodes = page.locator("svg[role='img'] circle");
    try {
      await nodes.first().waitFor({ timeout: 10000 });
    } catch {
      test.skip(true, "No graph nodes available");
    }
    // Let the force simulation settle so the node position is stable
    await page.waitForTimeout(1500);
    return nodes.first();
  }

  test("click selects a node and View note opens it", async ({ page }) => {
    const node = await firstNode(page);
    await node.click();

    const viewNote = page.getByRole("link", { name: /view note/i });
    await expect(viewNote).toBeVisible();

    await viewNote.click();
    await expect(page).toHaveURL(/\/knowledge-base\/notes\/[a-z0-9-]+$/);
  });

  test("double-click navigates to the note", async ({ page }) => {
    const node = await firstNode(page);
    await node.dblclick();

    await expect(page).toHaveURL(/\/knowledge-base\/notes\/[a-z0-9-]+$/);
  });
});

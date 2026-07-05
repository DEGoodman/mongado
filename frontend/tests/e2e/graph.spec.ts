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

  test("click with pointer travel (trackpad-style) still selects", async ({ page }) => {
    // Regression for #208: >10px of travel between mousedown and mouseup
    // used to be swallowed by d3's drag click-suppression
    await firstNode(page);
    const big = await page.evaluate(() => {
      const cs = Array.from(document.querySelectorAll("svg[role='img'] circle"));
      let best = null;
      let bestR = 0;
      for (const c of cs) {
        const r = c.getBoundingClientRect();
        if (r.width > bestR) {
          bestR = r.width;
          best = { x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }
      }
      return best;
    });
    if (!big) {
      test.skip(true, "No graph nodes available");
      return;
    }
    await page.mouse.move(big.x - 7, big.y - 7, { steps: 3 });
    await page.mouse.down();
    await page.mouse.move(big.x + 6, big.y + 6, { steps: 4 });
    await page.mouse.up();

    await expect(page.getByRole("link", { name: /view note/i })).toBeVisible();
  });

  test("double-click navigates to the note", async ({ page }) => {
    const node = await firstNode(page);
    await node.dblclick();

    await expect(page).toHaveURL(/\/knowledge-base\/notes\/[a-z0-9-]+$/);
  });
});

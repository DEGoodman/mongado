import { test, expect } from "@playwright/test";

/**
 * Regression test for issue #195: pages must never scroll horizontally
 * on a phone-sized viewport (iPhone 12/13/14 logical width).
 */
const PAGES = [
  "/",
  "/knowledge-base",
  "/knowledge-base/articles",
  "/knowledge-base/articles/1",
  "/knowledge-base/notes",
  "/knowledge-base/inspire",
];

test.use({ viewport: { width: 390, height: 844 } });

for (const path of PAGES) {
  test(`no horizontal overflow on ${path}`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const { viewportWidth, documentWidth } = await page.evaluate(() => ({
      viewportWidth: document.documentElement.clientWidth,
      documentWidth: document.documentElement.scrollWidth,
    }));
    expect(documentWidth, `document wider than viewport on ${path}`).toBeLessThanOrEqual(
      viewportWidth + 1
    );
  });
}

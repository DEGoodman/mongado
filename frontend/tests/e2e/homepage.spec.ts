import { test, expect } from "@playwright/test";

test.describe("Homepage", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("shows the name heading and page title", async ({ page }) => {
    await expect(page).toHaveTitle(/Mongado/);
    await expect(page.getByRole("heading", { level: 1, name: "D. Erik Goodman" })).toBeVisible();
  });

  test("links into the Knowledge Base", async ({ page }) => {
    await page.getByRole("link", { name: /Knowledge base/ }).click();
    await expect(page).toHaveURL(/\/knowledge-base$/);
  });

  test("links into the Library", async ({ page }) => {
    await page.getByRole("link", { name: /Library/ }).click();
    await expect(page).toHaveURL(/\/library$/);
  });

  test("theme toggle flips the theme", async ({ page }) => {
    const html = page.locator("html");
    const toggle = page.getByRole("button", { name: /Switch to (light|dark) theme/ });

    // The label names the theme the click switches *to*
    const label = await toggle.getAttribute("aria-label");
    const target = label?.includes("dark") ? "dark" : "light";
    await toggle.click();

    await expect(html).toHaveAttribute("data-theme", target);
  });
});

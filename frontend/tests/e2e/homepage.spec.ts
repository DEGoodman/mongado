import { test, expect } from "@playwright/test";

test.describe("Homepage", () => {
  test("should display the main heading", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Knowledge Base" })).toBeVisible();
  });

  test("should have Add Resource button", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("button", { name: /add resource/i })).toBeVisible();
  });

  test("should show form when Add Resource is clicked", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /add resource/i }).click();
    await expect(page.getByText("Add New Resource")).toBeVisible();
  });

  test("should create a new resource", async ({ page }) => {
    await page.goto("/");

    // Click Add Resource
    await page.getByRole("button", { name: /add resource/i }).click();

    // Fill in the form
    await page.getByLabel("Title").fill("Test Resource");
    await page.getByLabel("Content").fill("This is a test resource");
    await page.getByLabel("URL (optional)").fill("https://example.com");
    await page.getByLabel("Tags (comma-separated)").fill("test, example");

    // Submit the form
    await page.getByRole("button", { name: "Create Resource" }).click();

    // Verify the resource appears
    await expect(page.getByText("Test Resource")).toBeVisible();
  });
});

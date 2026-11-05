import { test, expect, type Page } from "@playwright/test";

/**
 * End-to-end passkey enrollment and login (#229), with the session carried
 * in an HttpOnly cookie (#311).
 *
 * Uses Chrome's WebAuthn virtual authenticator over CDP, so the full ceremony
 * runs for real - challenge, attestation, assertion, signature verification -
 * without a physical device. Chromium only; the CDP domain does not exist in
 * Firefox or WebKit.
 *
 * Enrollment needs the static admin token, which is what gates the first
 * passkey. Set E2E_ADMIN_TOKEN to run this; it skips without it.
 *
 * The test enrolls a device named DEVICE_NAME and revokes it at the end. It
 * also revokes any leftover of that name up front, because a stale row from
 * an interrupted run would otherwise satisfy the "enrolled" assertion without
 * anything actually having been enrolled - and the login step would then fail
 * against a credential this run's authenticator does not hold.
 */

const ADMIN_TOKEN = process.env.E2E_ADMIN_TOKEN;
const DEVICE_NAME = "E2E Device";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

test.describe("Passkey authentication", () => {
  test.skip(({ browserName }) => browserName !== "chromium", "Needs Chrome DevTools Protocol");
  test.skip(!ADMIN_TOKEN, "Set E2E_ADMIN_TOKEN to run passkey tests");

  /** Attach a virtual authenticator to this page's browser context. */
  async function addVirtualAuthenticator(page: Page): Promise<void> {
    const client = await page.context().newCDPSession(page);
    await client.send("WebAuthn.enable");
    await client.send("WebAuthn.addVirtualAuthenticator", {
      options: {
        protocol: "ctap2",
        transport: "internal",
        hasResidentKey: true,
        hasUserVerification: true,
        isUserVerified: true,
        automaticPresenceSimulation: true,
      },
    });
  }

  /** Remove any credential left behind by an earlier run. */
  async function revokeLeftovers(page: Page): Promise<void> {
    await page.request
      .get(`${API_URL}/api/auth/credentials`, {
        headers: { Authorization: `Bearer ${ADMIN_TOKEN}` },
      })
      .then(async (response) => {
        if (!response.ok()) return;
        const { credentials } = await response.json();
        for (const credential of credentials) {
          if (credential.name === DEVICE_NAME) {
            await page.request.delete(
              `${API_URL}/api/auth/credentials/${encodeURIComponent(credential.credential_id)}`,
              { headers: { Authorization: `Bearer ${ADMIN_TOKEN}` } }
            );
          }
        }
      });
  }

  /** Sign in with the static admin token, which passkey enrollment requires. */
  async function signInWithToken(page: Page): Promise<void> {
    await page.goto("/login");
    await page.getByRole("button", { name: /use an admin token instead/i }).click();
    await page.getByPlaceholder("Admin token").fill(ADMIN_TOKEN!);
    await page.getByRole("button", { name: /sign in with token/i }).click();
    await expect(page).toHaveURL(/\/knowledge-base\/notes/);
  }

  test("enrolls a passkey, then signs in with it", async ({ page }) => {
    await addVirtualAuthenticator(page);
    await revokeLeftovers(page);
    await signInWithToken(page);

    // Enroll from the admin page
    await page.goto("/admin");
    const enrolledRow = page.getByText(DEVICE_NAME, { exact: true });
    await expect(enrolledRow).toBeHidden();

    await page.getByPlaceholder(/device name/i).fill(DEVICE_NAME);
    await page.getByRole("button", { name: /add passkey/i }).click();
    await expect(enrolledRow).toBeVisible({ timeout: 15000 });

    // Sign out, then sign back in using only the passkey
    await page.context().clearCookies();
    await page.evaluate(() => localStorage.clear());
    await page.goto("/login");
    await page.getByRole("button", { name: /sign in with passkey/i }).click();
    await expect(page).toHaveURL(/\/knowledge-base\/notes/, { timeout: 15000 });

    // The credential is a session token in an HttpOnly cookie (#311) - not
    // the static admin token, and nothing page JavaScript can read
    const cookie = (await page.context().cookies(API_URL)).find(
      (c) => c.name === "mongado_session"
    );
    expect(cookie).toBeDefined();
    expect(cookie!.httpOnly).toBe(true);
    expect(cookie!.sameSite).toBe("Strict");
    expect(cookie!.value).not.toBe(ADMIN_TOKEN);

    const stored = await page.evaluate(() => ({
      keys: Object.keys(localStorage),
      expires: localStorage.getItem("admin_session_expires"),
      documentCookie: document.cookie,
    }));
    expect(stored.keys).not.toContain("admin_token");
    expect(stored.documentCookie).not.toContain("mongado_session");
    expect(Number(stored.expires)).toBeGreaterThan(Date.now());

    // Revoking removes it from the list
    await page.goto("/admin");
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: /revoke/i }).first().click();
    await expect(enrolledRow).toBeHidden({ timeout: 10000 });
  });
});

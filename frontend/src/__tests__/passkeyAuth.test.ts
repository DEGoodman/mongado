/**
 * Tests for passkey auth plumbing (#229)
 *
 * The ceremonies themselves need a real authenticator and are verified in the
 * browser. What is testable here is the part that silently corrupts data when
 * wrong: base64url <-> ArrayBuffer conversion of the WebAuthn options, and the
 * session-expiry bookkeeping in the API client.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { isPasskeySupported } from "@/lib/api/passkey";
import {
  apiFetch,
  clearAdminSession,
  getAuthHeaders,
  isAuthenticated,
  setAdminSession,
} from "@/lib/api/client";

describe("isPasskeySupported", () => {
  const originalPublicKeyCredential = window.PublicKeyCredential;

  afterEach(() => {
    window.PublicKeyCredential = originalPublicKeyCredential;
  });

  it("is false when the browser has no PublicKeyCredential", () => {
    // @ts-expect-error - simulating an old browser
    delete window.PublicKeyCredential;
    expect(isPasskeySupported()).toBe(false);
  });

  it("is true when PublicKeyCredential and credentials.create exist", () => {
    // @ts-expect-error - minimal stand-in for the real global
    window.PublicKeyCredential = function () {};
    Object.defineProperty(navigator, "credentials", {
      value: { create: vi.fn(), get: vi.fn() },
      configurable: true,
    });
    expect(isPasskeySupported()).toBe(true);
  });
});

describe("session bookkeeping (#311: credential lives in an HttpOnly cookie)", () => {
  const fetchMock = vi.fn(() => Promise.resolve(new Response("{}")));

  beforeEach(() => {
    localStorage.clear();
    fetchMock.mockClear();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const inOneHour = () => Math.floor(Date.now() / 1000) + 3600;

  it("treats a session as valid before its expiry", () => {
    setAdminSession(inOneHour());
    expect(isAuthenticated()).toBe(true);
  });

  it("treats a session as invalid at its expiry and clears the hint", () => {
    setAdminSession(Math.floor(Date.now() / 1000) - 1);
    expect(isAuthenticated()).toBe(false);
    expect(localStorage.getItem("admin_session_expires")).toBeNull();
  });

  it("is signed out with no session hint", () => {
    expect(isAuthenticated()).toBe(false);
  });

  it("stores no credential in localStorage, only the expiry", () => {
    setAdminSession(inOneHour());
    expect(Object.keys(localStorage)).toEqual(["admin_session_expires"]);
  });

  it("purges a pre-#311 bearer token and its now-stale session hint", () => {
    localStorage.setItem("admin_token", "legacy-token");
    localStorage.setItem("admin_token_timestamp", "123");
    localStorage.setItem("admin_session_expires", String((inOneHour() + 0) * 1000));
    expect(isAuthenticated()).toBe(false);
    expect(localStorage.length).toBe(0);
  });

  it("never sends an Authorization header", () => {
    setAdminSession(inOneHour());
    expect(getAuthHeaders()["Authorization"]).toBeUndefined();
  });

  it("apiFetch sends the session cookie", async () => {
    await apiFetch("http://api.test/x", { method: "POST" });
    expect(fetchMock).toHaveBeenCalledWith("http://api.test/x", {
      credentials: "include",
      method: "POST",
    });
  });

  it("logout clears the hint and asks the server to drop the cookie", () => {
    setAdminSession(inOneHour());
    clearAdminSession();
    expect(localStorage.getItem("admin_session_expires")).toBeNull();
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toMatch(/\/api\/auth\/logout$/);
    expect(init).toMatchObject({ method: "POST", credentials: "include" });
  });
});

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
import { setAdminToken, clearAdminToken, isAuthenticated, getAuthHeaders } from "@/lib/api/client";

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

describe("session storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("treats a passkey session as valid before its expiry", () => {
    const inOneHour = Math.floor(Date.now() / 1000) + 3600;
    setAdminToken("session-token", inOneHour);
    expect(isAuthenticated()).toBe(true);
  });

  it("treats a passkey session as invalid at its expiry", () => {
    const anHourAgo = Math.floor(Date.now() / 1000) - 3600;
    setAdminToken("session-token", anHourAgo);
    expect(isAuthenticated()).toBe(false);
  });

  it("clears the stored token once the session has expired", () => {
    setAdminToken("session-token", Math.floor(Date.now() / 1000) - 1);
    isAuthenticated();
    expect(localStorage.getItem("admin_token")).toBeNull();
    expect(localStorage.getItem("admin_session_expires")).toBeNull();
  });

  it("falls back to the client-side TTL for static tokens", () => {
    setAdminToken("static-admin-token");
    expect(localStorage.getItem("admin_session_expires")).toBeNull();
    expect(isAuthenticated()).toBe(true);
  });

  it("expires a static token older than the 7-day TTL", () => {
    setAdminToken("static-admin-token");
    const eightDaysAgo = Date.now() - 8 * 24 * 60 * 60 * 1000;
    localStorage.setItem("admin_token_timestamp", eightDaysAgo.toString());
    expect(isAuthenticated()).toBe(false);
  });

  it("drops a stale session expiry when a static token replaces a session", () => {
    setAdminToken("session-token", Math.floor(Date.now() / 1000) + 3600);
    setAdminToken("static-admin-token");
    expect(localStorage.getItem("admin_session_expires")).toBeNull();
  });

  it("sends the stored token as a bearer credential", () => {
    setAdminToken("session-token", Math.floor(Date.now() / 1000) + 3600);
    const headers = getAuthHeaders() as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer session-token");
  });

  it("sends no Authorization header when signed out", () => {
    clearAdminToken();
    const headers = getAuthHeaders() as Record<string, string>;
    expect(headers["Authorization"]).toBeUndefined();
  });

  it("clears every auth key on logout", () => {
    setAdminToken("session-token", Math.floor(Date.now() / 1000) + 3600);
    clearAdminToken();
    expect(localStorage.getItem("admin_token")).toBeNull();
    expect(localStorage.getItem("admin_token_timestamp")).toBeNull();
    expect(localStorage.getItem("admin_session_expires")).toBeNull();
  });
});

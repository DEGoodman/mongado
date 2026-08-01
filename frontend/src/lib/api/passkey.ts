/**
 * Passkey (WebAuthn) authentication (#229).
 *
 * The browser's credential APIs speak ArrayBuffer; the backend speaks
 * base64url JSON. This module is the translation layer plus the four
 * ceremony calls, so the pages stay free of buffer juggling.
 */

import { apiDelete, apiGet, apiPost, setAdminToken } from "./client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface PasskeyCredential {
  credential_id: string;
  name: string;
  created_at: number;
  last_used_at: number | null;
}

interface CredentialsListResponse {
  credentials: PasskeyCredential[];
  count: number;
}

export interface SessionStatus {
  authenticated: boolean;
  kind: "passkey" | "token" | "none";
  expires_at: number | null;
}

interface SessionResponse {
  token: string;
  expires_at: number;
  credential_name: string;
}

/** Whether this browser can do passkeys at all. */
export function isPasskeySupported(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.PublicKeyCredential !== "undefined" &&
    typeof navigator.credentials?.create === "function"
  );
}

function base64urlToBuffer(value: string): ArrayBuffer {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(padded + "=".repeat((4 - (padded.length % 4)) % 4));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

function bufferToBase64url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

/**
 * Decode the base64url fields the backend sends into the buffers the
 * browser requires. Only the fields WebAuthn defines as BufferSource are
 * converted; everything else passes through untouched.
 */
function decodeCreationOptions(
  options: Record<string, unknown>
): PublicKeyCredentialCreationOptions {
  const decoded = { ...options } as Record<string, unknown>;
  decoded.challenge = base64urlToBuffer(options.challenge as string);

  const user = options.user as Record<string, unknown>;
  decoded.user = { ...user, id: base64urlToBuffer(user.id as string) };

  const exclude = options.excludeCredentials as Array<Record<string, unknown>> | undefined;
  if (exclude) {
    decoded.excludeCredentials = exclude.map((credential) => ({
      ...credential,
      id: base64urlToBuffer(credential.id as string),
    }));
  }

  return decoded as unknown as PublicKeyCredentialCreationOptions;
}

function decodeRequestOptions(options: Record<string, unknown>): PublicKeyCredentialRequestOptions {
  const decoded = { ...options } as Record<string, unknown>;
  decoded.challenge = base64urlToBuffer(options.challenge as string);

  const allow = options.allowCredentials as Array<Record<string, unknown>> | undefined;
  if (allow) {
    decoded.allowCredentials = allow.map((credential) => ({
      ...credential,
      id: base64urlToBuffer(credential.id as string),
    }));
  }

  return decoded as unknown as PublicKeyCredentialRequestOptions;
}

/** Re-encode an authenticator's response into the JSON shape py_webauthn parses. */
function encodeRegistrationCredential(credential: PublicKeyCredential): Record<string, unknown> {
  const response = credential.response as AuthenticatorAttestationResponse;
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      attestationObject: bufferToBase64url(response.attestationObject),
    },
    clientExtensionResults: credential.getClientExtensionResults(),
  };
}

function encodeAuthenticationCredential(credential: PublicKeyCredential): Record<string, unknown> {
  const response = credential.response as AuthenticatorAssertionResponse;
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      authenticatorData: bufferToBase64url(response.authenticatorData),
      signature: bufferToBase64url(response.signature),
      userHandle: response.userHandle ? bufferToBase64url(response.userHandle) : null,
    },
    clientExtensionResults: credential.getClientExtensionResults(),
  };
}

/**
 * Enroll a new passkey. Requires an already-authenticated session (the
 * static admin token for the first one, a passkey session after that).
 */
export async function registerPasskey(name: string): Promise<PasskeyCredential[]> {
  const { options } = await apiPost<{ options: Record<string, unknown> }>(
    "/api/auth/register/options",
    { name }
  );

  const credential = (await navigator.credentials.create({
    publicKey: decodeCreationOptions(options),
  })) as PublicKeyCredential | null;

  if (!credential) {
    throw new Error("Passkey creation was cancelled.");
  }

  const result = await apiPost<CredentialsListResponse>("/api/auth/register/verify", {
    credential: encodeRegistrationCredential(credential),
    name,
  });
  return result.credentials;
}

/**
 * Sign in with a passkey and store the resulting session.
 *
 * Deliberately not routed through apiPost: these two calls must not carry a
 * stale Authorization header, and their errors need to reach the UI with the
 * backend's own wording (e.g. "No passkeys registered").
 */
export async function loginWithPasskey(): Promise<{ expiresAt: number; credentialName: string }> {
  const optionsResponse = await fetch(`${API_BASE_URL}/api/auth/login/options`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!optionsResponse.ok) {
    const body = await optionsResponse.json().catch(() => ({ detail: "Login unavailable" }));
    throw new Error(body.detail || "Could not start passkey login.");
  }
  const { options } = await optionsResponse.json();

  const credential = (await navigator.credentials.get({
    publicKey: decodeRequestOptions(options),
  })) as PublicKeyCredential | null;

  if (!credential) {
    throw new Error("Passkey login was cancelled.");
  }

  const verifyResponse = await fetch(`${API_BASE_URL}/api/auth/login/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential: encodeAuthenticationCredential(credential) }),
  });
  if (!verifyResponse.ok) {
    const body = await verifyResponse.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(body.detail || "Passkey login failed.");
  }

  const session: SessionResponse = await verifyResponse.json();
  setAdminToken(session.token, session.expires_at);
  return { expiresAt: session.expires_at, credentialName: session.credential_name };
}

/** Ask the backend whether the stored credentials are still good. */
export async function getSessionStatus(): Promise<SessionStatus> {
  return apiGet<SessionStatus>("/api/auth/session");
}

export async function listPasskeys(): Promise<PasskeyCredential[]> {
  const response = await apiGet<CredentialsListResponse>("/api/auth/credentials");
  return response.credentials;
}

export async function deletePasskey(credentialId: string): Promise<void> {
  await apiDelete(`/api/auth/credentials/${encodeURIComponent(credentialId)}`);
}

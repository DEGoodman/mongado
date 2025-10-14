"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { setAdminToken } from "@/lib/api/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      // Store the token first so the API client can use it
      setAdminToken(token);

      // Test the token by making an authenticated request to create a note
      // This endpoint requires auth, so it will validate our token
      const response = await fetch(`${API_URL}/api/notes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          content: "# Test Auth\n\nTemporary note to validate authentication",
          title: "Auth Test",
        }),
      });

      if (response.ok) {
        // Token is valid, delete the test note
        const testNote = await response.json();

        await fetch(`${API_URL}/api/notes/${testNote.id}`, {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        // Redirect to notes page
        router.push("/knowledge-base/notes");
      } else {
        const data = await response.json().catch(() => ({ detail: "Invalid token" }));
        setError(data.detail || "Invalid token");
        // Clear the stored token on failure
        setAdminToken("");
      }
    } catch (err) {
      setError("Failed to connect to server");
      // Clear the stored token on failure
      setAdminToken("");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            Admin Login
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Enter your admin token to create persistent notes
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleLogin}>
          <div className="-space-y-px rounded-md shadow-sm">
            <div>
              <label htmlFor="token" className="sr-only">
                Admin Token
              </label>
              <input
                id="token"
                name="token"
                type="password"
                autoComplete="current-password"
                required
                className="relative block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-500 focus:z-10 focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
                placeholder="Admin token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                disabled={isLoading}
              />
            </div>
          </div>

          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-red-800">{error}</p>
                </div>
              </div>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative flex w-full justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:bg-gray-400"
            >
              {isLoading ? "Verifying..." : "Sign in"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

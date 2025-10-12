"use client";

import { useEffect, useState } from "react";

interface AuthStatusBannerProps {
  /**
   * Display mode: "warning" for unauthenticated, "success" for authenticated
   */
  mode?: "auto" | "warning" | "success";
}

export default function AuthStatusBanner({ mode = "auto" }: AuthStatusBannerProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    // Check authentication status
    // For now, we check if there's an admin passkey in localStorage
    // TODO: Replace with actual auth check against backend
    const checkAuth = async () => {
      try {
        const adminPasskey = localStorage.getItem("admin_passkey");
        setIsAuthenticated(!!adminPasskey);
      } catch (err) {
        setIsAuthenticated(false);
      } finally {
        setIsChecking(false);
      }
    };

    checkAuth();
  }, []);

  if (isChecking) {
    return null; // Don't show anything while checking
  }

  const displayMode = mode === "auto" ? (isAuthenticated ? "success" : "warning") : mode;

  if (displayMode === "success" && isAuthenticated) {
    return (
      <div className="bg-green-50 border-l-4 border-green-500 p-3 mb-4">
        <div className="flex items-center">
          <svg
            className="w-5 h-5 text-green-500 mr-3"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          <div className="flex-1">
            <p className="text-sm font-medium text-green-800">Authenticated</p>
            <p className="text-xs text-green-700 mt-0.5">
              Your notes will be saved persistently to the database
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (displayMode === "warning" && !isAuthenticated) {
    return (
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
        <div className="flex items-start">
          <svg
            className="w-5 h-5 text-yellow-400 mr-3 mt-0.5"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          <div className="flex-1">
            <p className="text-sm font-medium text-yellow-800">
              You are not authenticated
            </p>
            <p className="text-xs text-yellow-700 mt-1">
              <strong>Your notes are ephemeral</strong> - they will only be visible in this
              browser session and will be lost when you close the tab or after 24 hours of
              inactivity.
            </p>
            <p className="text-xs text-yellow-700 mt-2">
              <strong>What this means:</strong>
            </p>
            <ul className="text-xs text-yellow-700 mt-1 ml-4 list-disc space-y-0.5">
              <li>Notes are stored in memory only (not in the database)</li>
              <li>Other users won't see your ephemeral notes</li>
              <li>You can still link notes together with [[wikilinks]]</li>
              <li>Session persists across page refreshes in the same browser</li>
            </ul>
            <div className="mt-3 pt-3 border-t border-yellow-200">
              <p className="text-xs text-yellow-700">
                <strong>To save notes permanently:</strong> Contact the admin for an access
                passkey
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

/**
 * Compact authentication indicator for the top of pages
 */
export function AuthStatusIndicator() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const adminPasskey = localStorage.getItem("admin_passkey");
        setIsAuthenticated(!!adminPasskey);
      } catch (err) {
        setIsAuthenticated(false);
      } finally {
        setIsChecking(false);
      }
    };

    checkAuth();
  }, []);

  if (isChecking) {
    return null;
  }

  return (
    <div
      className={`text-xs py-1 px-3 text-center ${
        isAuthenticated
          ? "bg-green-500 text-white"
          : "bg-yellow-100 text-yellow-800"
      }`}
    >
      {isAuthenticated ? (
        <span>
          ✓ Authenticated - Notes will be saved permanently
        </span>
      ) : (
        <span>
          ⚠ Not authenticated - Ephemeral notes only (session-based)
        </span>
      )}
    </div>
  );
}

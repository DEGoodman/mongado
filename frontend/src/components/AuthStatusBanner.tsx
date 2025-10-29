"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearAdminToken } from "@/lib/api/client";

interface AuthStatusBannerProps {
  /**
   * Display mode: "warning" for unauthenticated, "success" for authenticated
   */
  mode?: "auto" | "warning" | "success";
}

export default function AuthStatusBanner({ mode = "auto" }: AuthStatusBannerProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const router = useRouter();

  const checkAuth = () => {
    try {
      const adminToken = localStorage.getItem("admin_token");
      setIsAuthenticated(!!adminToken);
    } catch (err) {
      setIsAuthenticated(false);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const handleLogout = () => {
    clearAdminToken();
    setIsAuthenticated(false);
    router.push("/knowledge-base/notes");
  };

  if (isChecking) {
    return null; // Don't show anything while checking
  }

  const displayMode = mode === "auto" ? (isAuthenticated ? "success" : "warning") : mode;

  if (displayMode === "success" && isAuthenticated) {
    return (
      <div className="mb-4 border-l-4 border-green-500 bg-green-50 p-3">
        <div className="flex items-center">
          <svg className="mr-3 h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          <div className="flex-1">
            <p className="text-sm font-medium text-green-800">Authenticated</p>
            <p className="mt-0.5 text-xs text-green-700">
              Your notes will be saved persistently to the database
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="ml-3 rounded-md bg-green-100 px-3 py-1 text-xs font-medium text-green-800 hover:bg-green-200"
          >
            Logout
          </button>
        </div>
      </div>
    );
  }

  if (displayMode === "warning" && !isAuthenticated) {
    return (
      <div className="mb-4 border-l-4 border-yellow-400 bg-yellow-50 p-4">
        <div className="flex items-start">
          <svg
            className="mr-3 mt-0.5 h-5 w-5 text-yellow-400"
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
            <p className="text-sm font-medium text-yellow-800">You are not authenticated</p>
            <p className="mt-1 text-xs text-yellow-700">
              <strong>Authentication is required</strong> to create, edit, or delete notes.
              You can view existing notes, but cannot make changes.
            </p>
            <div className="mt-3 border-t border-yellow-200 pt-3">
              <p className="text-xs text-yellow-700">
                <strong>To manage notes:</strong>{" "}
                <Link href="/login" className="font-medium underline hover:text-yellow-900">
                  Login with admin token
                </Link>
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
        const adminToken = localStorage.getItem("admin_token");
        setIsAuthenticated(!!adminToken);
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
      className={`px-3 py-1 text-center text-xs ${
        isAuthenticated ? "bg-green-500 text-white" : "bg-yellow-100 text-yellow-800"
      }`}
    >
      {isAuthenticated ? (
        <span>✓ Authenticated - Notes will be saved permanently</span>
      ) : (
        <span>⚠ Not authenticated - Login required to create or edit notes</span>
      )}
    </div>
  );
}

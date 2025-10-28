"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useSettings } from "@/hooks/useSettings";
import type { AiMode } from "@/lib/settings";
import { logger } from "@/lib/logger";
import { isAuthenticated, clearAdminToken } from "@/lib/api/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SettingsDropdown() {
  const { settings, updateSettings } = useSettings();
  const [isOpen, setIsOpen] = useState(false);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [isUserAuthenticated, setIsUserAuthenticated] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Check authentication status on mount and when dropdown opens
  useEffect(() => {
    setIsUserAuthenticated(isAuthenticated());
  }, [isOpen]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  const warmupOllama = async () => {
    setIsWarmingUp(true);
    try {
      const response = await fetch(`${API_URL}/api/ollama/warmup`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Warmup failed");
      }

      logger.info("Ollama warmed up successfully");
    } catch (err) {
      logger.error("Failed to warm up Ollama", err);
      // Don't block the setting change - warmup will happen on first use
    } finally {
      setIsWarmingUp(false);
    }
  };

  const handleModeChange = async (newMode: AiMode) => {
    const oldMode = settings.aiMode;
    updateSettings({ aiMode: newMode });

    // Warmup if switching from "off" to an AI-enabled mode
    if (oldMode === "off" && (newMode === "on-demand" || newMode === "real-time")) {
      await warmupOllama();
    }
  };

  const handleLogout = () => {
    clearAdminToken();
    logger.info("User logged out");
    setIsOpen(false);
    router.push("/login");
  };

  return (
    <div className="flex items-center gap-3">
      {/* Sign In link when not authenticated */}
      {!isUserAuthenticated && (
        <Link
          href="/login"
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-blue-600 transition-colors hover:bg-blue-50"
        >
          Sign In
        </Link>
      )}

      {/* Settings dropdown */}
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-gray-700 transition-colors hover:bg-gray-100"
          aria-label="Settings"
        >
          <span className="text-lg">⚙️</span>
          <span className="text-sm font-medium">Settings</span>
          <svg
            className={`h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {isOpen && (
          <div className="absolute right-0 z-50 mt-2 w-80 rounded-lg border border-gray-200 bg-white shadow-lg">
            <div className="p-4">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">AI Suggestions</h3>
                {isWarmingUp && <span className="text-xs text-gray-500">Warming up...</span>}
              </div>

              {/* Segmented Control */}
              <div className="flex rounded-lg bg-gray-100 p-1">
                <button
                  onClick={() => handleModeChange("off")}
                  className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-all ${
                    settings.aiMode === "off"
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  Off
                </button>
                <button
                  onClick={() => handleModeChange("on-demand")}
                  className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-all ${
                    settings.aiMode === "on-demand"
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  On-demand
                </button>
                <button
                  onClick={() => handleModeChange("real-time")}
                  className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-all ${
                    settings.aiMode === "real-time"
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  Automatic
                </button>
              </div>

              {/* Mode descriptions */}
              <div className="mt-3 text-xs text-gray-600">
                {settings.aiMode === "off" && (
                  <p>No AI suggestions. Fast, minimal overhead. Pure Zettelkasten experience.</p>
                )}
                {settings.aiMode === "on-demand" && (
                  <p>
                    Click &quot;Get Suggestions&quot; when you want AI help. Balanced approach with
                    no overhead while writing.
                  </p>
                )}
                {settings.aiMode === "real-time" && (
                  <p>
                    Automatically generate suggestions in the background as you type. Panel stays
                    collapsed until you open it.
                  </p>
                )}
              </div>

              {/* Logout section */}
              {isUserAuthenticated && (
                <div className="mt-4 border-t border-gray-200 pt-3">
                  <button
                    onClick={handleLogout}
                    className="w-full rounded-md px-3 py-2 text-left text-sm font-medium text-red-600 transition-colors hover:bg-red-50"
                  >
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

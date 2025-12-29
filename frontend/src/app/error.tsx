"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Application error:", error);
  }, [error]);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "var(--font-space-grotesk), sans-serif",
        background: "linear-gradient(to bottom right, #fef2f2, #fef2f2)",
      }}
    >
      <h1
        style={{
          fontSize: "4rem",
          fontWeight: "700",
          color: "#dc2626",
          margin: "0",
        }}
      >
        Oops!
      </h1>
      <h2
        style={{
          fontSize: "1.5rem",
          fontWeight: "600",
          color: "#7f1d1d",
          margin: "0.5rem 0 1rem",
        }}
      >
        Something went wrong
      </h2>
      <p
        style={{
          color: "#6b7280",
          marginBottom: "2rem",
          textAlign: "center",
          maxWidth: "400px",
        }}
      >
        An unexpected error occurred. Please try again.
      </p>
      <button
        onClick={reset}
        style={{
          padding: "0.75rem 1.5rem",
          backgroundColor: "#dc2626",
          color: "white",
          borderRadius: "0.5rem",
          border: "none",
          fontWeight: "500",
          cursor: "pointer",
          fontFamily: "inherit",
        }}
      >
        Try Again
      </button>
    </div>
  );
}

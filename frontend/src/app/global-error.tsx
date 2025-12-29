"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body>
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "system-ui, sans-serif",
            background: "#fef2f2",
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
            Error
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
            }}
          >
            Try Again
          </button>
        </div>
      </body>
    </html>
  );
}

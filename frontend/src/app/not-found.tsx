import Link from "next/link";

export default function NotFound() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "var(--font-space-grotesk), sans-serif",
        background: "linear-gradient(to bottom right, #f0fdf4, #ecfdf5)",
      }}
    >
      <h1
        style={{
          fontSize: "6rem",
          fontWeight: "700",
          color: "#0d9488",
          margin: "0",
        }}
      >
        404
      </h1>
      <h2
        style={{
          fontSize: "1.5rem",
          fontWeight: "600",
          color: "#134e4a",
          margin: "0.5rem 0 1rem",
        }}
      >
        Page Not Found
      </h2>
      <p
        style={{
          color: "#5f6d64",
          marginBottom: "2rem",
          textAlign: "center",
          maxWidth: "400px",
        }}
      >
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <Link
        href="/"
        style={{
          padding: "0.75rem 1.5rem",
          backgroundColor: "#0d9488",
          color: "white",
          borderRadius: "0.5rem",
          textDecoration: "none",
          fontWeight: "500",
        }}
      >
        Go Home
      </Link>
    </div>
  );
}

import bundleAnalyzer from "@next/bundle-analyzer";

// API origin for CSP allowlists (browser fetches + images served by the API)
const apiOrigin = new URL(process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").origin;
const isDev = process.env.NODE_ENV !== "production";

// Content-Security-Policy for the frontend origin (#172).
//
// script-src keeps 'unsafe-inline' deliberately: Next.js injects dynamic
// inline hydration scripts that cannot be hash-allowlisted, and nonce-based
// CSP forces every page to render dynamically, which conflicts with the SSG
// goal (#207). Everything else is strict — external script/style/img/connect
// origins are all blocked. Dev additionally needs 'unsafe-eval' (react
// refresh) and ws: (HMR socket).
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: blob: ${apiOrigin}`,
  `connect-src 'self' ${apiOrigin}${isDev ? " ws:" : ""}`,
  "font-src 'self' data:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  poweredByHeader: false,

  // isomorphic-dompurify uses jsdom on the server, which reads its
  // default-stylesheet.css from disk at runtime - bundling it breaks that
  // path resolution (ENOENT), so require it from node_modules instead
  serverExternalPackages: ["isomorphic-dompurify"],

  // Rewrite @phosphor-icons/react barrel imports to per-icon imports.
  // Without this, webpack compiles all ~9,000 icons into every route that
  // renders the nav (10k+ modules, 10s+ dev compiles).
  experimental: {
    optimizePackageImports: ["@phosphor-icons/react"],
  },

  async headers() {
    return [
      {
        source: "/:path*",
        headers: [{ key: "Content-Security-Policy", value: csp }],
      },
    ];
  },
};

// Bundle analyzer (npm run build:analyze / make build-frontend-analyze)
const withBundleAnalyzer = bundleAnalyzer({ enabled: process.env.ANALYZE === "true" });

export default withBundleAnalyzer(nextConfig);

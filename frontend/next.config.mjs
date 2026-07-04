/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',

  // Rewrite @phosphor-icons/react barrel imports to per-icon imports.
  // Without this, webpack compiles all ~9,000 icons into every route that
  // renders the nav (10k+ modules, 10s+ dev compiles).
  experimental: {
    optimizePackageImports: ['@phosphor-icons/react'],
  },
};

export default nextConfig;

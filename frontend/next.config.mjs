import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "..");
const IGNORED_WATCH_PATTERNS = [
  path.join(repoRoot, "data"),
  path.join(repoRoot, "docs"),
  path.join(repoRoot, "scripts"),
  path.join(repoRoot, "scraper"),
  path.join(repoRoot, "tests"),
].map((dir) => `${dir}/**`);

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Remove standalone output for Vercel (it's not needed)
  // output: 'standalone',

  // Disable image optimization for cPanel compatibility
  images: {
    unoptimized: true,
  },

  // Base path for subdirectory deployment (e.g., /ufc)
  basePath: process.env.BASEPATH || '',

  // Fix date-fns barrel optimization issue
  experimental: {
    optimizePackageImports: ['date-fns'],
  },

  // Remove rewrites - use NEXT_PUBLIC_API_BASE_URL directly in your API client
  // async rewrites() { ... }
  webpack: (config, { dev }) => {
    if (!dev) {
      return config;
    }

    const existingIgnored = config.watchOptions?.ignored ?? [];
    const normalizedIgnored = Array.isArray(existingIgnored)
      ? existingIgnored.filter(Boolean)
      : [existingIgnored].filter(Boolean);

    config.watchOptions = {
      ...config.watchOptions,
      ignored: [...new Set([...normalizedIgnored, ...IGNORED_WATCH_PATTERNS])],
    };

    return config;
  },
};

export default nextConfig;

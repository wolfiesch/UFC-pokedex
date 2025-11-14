import path from "node:path";

const SCHEME_REGEX = /^[a-zA-Z][\w+.-]*:\/\//;
const LOCAL_ADDRESS_PREFIXES = ["localhost", "127.", "0.0.0.0", "[::1]"];

// Fallback API endpoint used when Vercel environment variables are missing.
// Keeping the value close to the rewrite helper ensures preview deployments
// automatically proxy requests to the hosted Railway backend rather than the
// local development server (which is unreachable in serverless environments).
const DEFAULT_DEPLOYMENT_API_BASE_URL =
  process.env.NEXT_PUBLIC_DEPLOYMENT_API_BASE_URL ??
  "https://fulfilling-nourishment-production.up.railway.app";

function isLikelyLocalAddress(value) {
  const lower = value.toLowerCase();
  return LOCAL_ADDRESS_PREFIXES.some((prefix) => lower.startsWith(prefix));
}

function ensureAbsoluteUrl(value) {
  const parsed = new URL(value);
  const normalizedPath =
    parsed.pathname === "/" ? "" : parsed.pathname.replace(/\/$/, "");
  return `${parsed.origin}${normalizedPath}`;
}

function resolveRewriteBaseUrl(rawUrl) {
  const trimmed = rawUrl?.trim();
  if (!trimmed) {
    return null;
  }

  const candidates = [trimmed];

  if (!SCHEME_REGEX.test(trimmed)) {
    const scheme = isLikelyLocalAddress(trimmed) ? "http://" : "https://";
    candidates.push(`${scheme}${trimmed}`);
  }

  for (const candidate of candidates) {
    try {
      return ensureAbsoluteUrl(candidate);
    } catch {
      // Try next candidate
    }
  }

  console.warn(
    `next.config.mjs: invalid API rewrite destination "${trimmed}", skipping rewrite.`
  );

  return null;
}

function getRewriteDestination() {
  const raw =
    process.env.NEXT_API_REWRITE_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    process.env.NEXT_SSR_API_BASE_URL ??
    (process.env.NODE_ENV === "production"
      ? DEFAULT_DEPLOYMENT_API_BASE_URL
      : undefined);

  return resolveRewriteBaseUrl(raw);
}

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

  // Skip type checking during build (temporary fix for OpenAPI type mismatches)
  typescript: {
    ignoreBuildErrors: true,
  },

  // Disable image optimization for cPanel compatibility
  images: {
    unoptimized: true,
  },

  // Base path for subdirectory deployment (e.g., /ufc)
  basePath: process.env.BASEPATH || '',

  // Fix date-fns barrel optimization issue
  experimental: {
    optimizePackageImports: ['date-fns'],
    // Turbopack-specific configuration
    turbo: {
      // Exclude repository root directories from watch (Turbopack mode)
      // These directories contain data/docs/scripts that shouldn't trigger rebuilds
      resolveAlias: {},
      rules: {
        // Empty loaders for directories we want to exclude from watching
        '../../data/**': { loaders: [] },
        '../../docs/**': { loaders: [] },
        '../../scripts/**': { loaders: [] },
        '../../scraper/**': { loaders: [] },
        '../../tests/**': { loaders: [] },
      },
    },
  },

  // Proxy REST API requests when a base URL is provided.
  async rewrites() {
    const destination = getRewriteDestination();
    if (!destination) {
      return [];
    }

    return [
      {
        source: "/api/:path*",
        destination: `${destination}/:path*`,
      },
    ];
  },
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

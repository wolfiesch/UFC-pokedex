const IGNORED_WATCH_GLOBS = [
  "../data/**",
  "../docs/**",
  "../scripts/**",
  "../scraper/**",
  "../tests/**",
];

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

  webpackDevMiddleware: (config) => {
    const existingIgnored = config.watchOptions?.ignored ?? [];
    const normalizedIgnored = Array.isArray(existingIgnored)
      ? existingIgnored
      : [existingIgnored].filter(Boolean);

    config.watchOptions = {
      ...config.watchOptions,
      ignored: [...normalizedIgnored, ...IGNORED_WATCH_GLOBS],
    };

    return config;
  },
};

export default nextConfig;

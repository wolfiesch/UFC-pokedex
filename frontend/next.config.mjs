/** @type {import('next').NextConfig} */
const API_PROXY_TARGET =
  process.env.NEXT_SSR_API_BASE_URL || "http://localhost:8000";

const normalizedApiTarget = API_PROXY_TARGET.replace(/\/+$/, "");

const nextConfig = {
  // Standalone output for Node.js deployment
  output: 'standalone',

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

  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${normalizedApiTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;

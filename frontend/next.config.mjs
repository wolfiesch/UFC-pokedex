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
};

export default nextConfig;

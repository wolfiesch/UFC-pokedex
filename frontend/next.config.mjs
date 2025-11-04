/** @type {import('next').NextConfig} */
const nextConfig = {
  // Use 'export' for static HTML generation (for cPanel deployment)
  // Use 'standalone' for Node.js server deployment (for Cloudflare tunnel)
  output: process.env.BUILD_MODE === 'static' ? 'export' : 'standalone',

  // Disable image optimization for static export (cPanel doesn't support it)
  images: {
    unoptimized: process.env.BUILD_MODE === 'static',
  },

  // Optional: Add base path if deploying to subdirectory
  // basePath: process.env.NEXT_PUBLIC_BASE_PATH || '',
};

export default nextConfig;

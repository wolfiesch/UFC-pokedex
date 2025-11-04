/** @type {import('next').NextConfig} */
const nextConfig = {
  // Standalone output for Node.js deployment
  output: 'standalone',

  // Disable image optimization for cPanel compatibility
  images: {
    unoptimized: true,
  },

  // Base path for subdirectory deployment (e.g., /ufc)
  basePath: process.env.BASEPATH || '',
};

export default nextConfig;

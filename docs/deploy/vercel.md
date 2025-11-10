# Vercel Deployment with pnpm

This project deploys the Next.js frontend on Vercel. To ensure consistent builds and take full advantage of Vercel's dependency caching, we standardize on **pnpm** for all install, build, and development tasks.

## Vercel Command Configuration

Vercel is configured with the following commands, which are run from the repository root:

- **Install Command:** `cd frontend && corepack enable && pnpm install`
  - Enables Corepack so pnpm is available in the build image.
  - Installs dependencies using the lockfile at `frontend/pnpm-lock.yaml`.
- **Build Command:** `cd frontend && pnpm run build`
  - Builds the Next.js application using pnpm scripts.
- **Development Command:** `cd frontend && pnpm run dev`
  - Defines the development command for preview deployments or local Vercel CLI usage.

Keep the `frontend/pnpm-lock.yaml` file committed and up to date. Vercel caches dependencies based on this lockfile, so any dependency changes must update the lockfile to avoid cache misses or mismatched installs.

## Local Reproduction

When debugging Vercel builds locally:

```bash
cd frontend
corepack enable
pnpm install
pnpm run build
```

This mirrors the Vercel build steps and helps detect issues before pushing changes.

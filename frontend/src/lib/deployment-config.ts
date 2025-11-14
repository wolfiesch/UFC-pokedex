/**
 * Shared deployment-aware configuration helpers.
 *
 * The production deployment currently runs on Railway under the
 * `fulfilling-nourishment-production` service.  Several modules need a
 * canonical reference to that base URL when environment variables are not
 * present (which happens on freshly provisioned Vercel projects or preview
 * deployments).  Centralising the value keeps future domain changes confined to
 * a single location and guarantees every consumer follows the same fallback
 * rules.
 */

/**
 * Base URL for the hosted FastAPI backend used by public deployments.
 *
 * - `NEXT_PUBLIC_DEPLOYMENT_API_BASE_URL` provides an override that keeps the
 *   value configurable without code changes.
 * - When the override is absent we fall back to the known Railway deployment.
 */
export const DEFAULT_DEPLOYMENT_API_BASE_URL: string =
  process.env.NEXT_PUBLIC_DEPLOYMENT_API_BASE_URL ??
  "https://fulfilling-nourishment-production.up.railway.app";

/**
 * Determine the default API base URL for the current runtime environment.
 *
 * @param developmentUrl - Absolute URL pointing at the developer-friendly API
 *   instance.  The argument keeps local tooling testable (e.g. unit tests or
 *   Storybook) while still allowing overrides in rare scenarios.
 * @returns An absolute base URL string that callers can safely feed into
 *   `resolveApiBaseUrl` without additional guards.
 */
export function getDefaultApiBaseUrl(
  developmentUrl: string = "http://localhost:8000",
): string {
  return process.env.NODE_ENV === "production"
    ? DEFAULT_DEPLOYMENT_API_BASE_URL
    : developmentUrl;
}

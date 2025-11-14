import { resolveApiBaseUrl } from "./resolve-api-base-url";
import { getDefaultApiBaseUrl } from "./deployment-config";

const LOCAL_HOSTNAME_REGEX =
  /^(?:localhost|127(?:\.\d+){3}|0\.0\.0\.0|\[::1\])$/i;

type NextData = {
  assetPrefix?: string;
};

function isBrowserEnvironment(): boolean {
  return (
    typeof window !== "undefined" && typeof window.location !== "undefined"
  );
}

function getBasePathFromNextData(nextData?: NextData): string {
  const assetPrefix = nextData?.assetPrefix;
  if (!assetPrefix || typeof assetPrefix !== "string") {
    return "";
  }

  // assetPrefix may include protocol/CDN; only keep the path portion
  try {
    const parsed = new URL(assetPrefix, "http://example.com");
    return parsed.pathname === "/" ? "" : parsed.pathname.replace(/\/$/, "");
  } catch {
    return assetPrefix.startsWith("/")
      ? assetPrefix.replace(/\/$/, "")
      : `/${assetPrefix}`.replace(/\/$/, "");
  }
}

function inferBrowserApiBaseUrl(): string | undefined {
  if (!isBrowserEnvironment()) {
    return undefined;
  }

  const { origin, hostname } = window.location;
  if (!origin || !hostname) {
    return undefined;
  }

  if (LOCAL_HOSTNAME_REGEX.test(hostname)) {
    return undefined;
  }

  const nextData = (
    globalThis as typeof globalThis & {
      __NEXT_DATA__?: NextData;
    }
  ).__NEXT_DATA__;

  const basePath = getBasePathFromNextData(nextData);
  const apiPath = `${basePath}/api`.replace(/\/{2,}/g, "/");

  return `${origin}${apiPath.startsWith("/") ? apiPath : `/${apiPath}`}`;
}

/**
 * Default API base URL that adapts to the runtime environment.
 *
 * Local development keeps using the FastAPI server on port 8000 while
 * production/preview deployments transparently fall back to the hosted Railway
 * backend.  Centralising the logic prevents individual modules from shipping
 * out-of-date hard-coded URLs when environment variables are missing.
 */
export const DEFAULT_CLIENT_API_BASE_URL: string = getDefaultApiBaseUrl();

/**
 * Resolves the API base URL for client-side usage, with smart fallbacks.
 *
 * Priority:
 * 1. Use the configured environment variable if present.
 * 2. In the browser, fall back to the current origin + "/api" (Next.js rewrite).
 * 3. Finally, use the provided fallback (defaults to localhost).
 */
export function resolveClientApiBaseUrl(
  configuredUrl: string | undefined,
  fallbackUrl = DEFAULT_CLIENT_API_BASE_URL,
): string {
  if (configuredUrl?.trim()) {
    return resolveApiBaseUrl(configuredUrl, fallbackUrl);
  }

  const inferred = inferBrowserApiBaseUrl();
  if (inferred) {
    try {
      return resolveApiBaseUrl(inferred, fallbackUrl);
    } catch (error) {
      if (typeof console !== "undefined") {
        console.warn(
          `resolveClientApiBaseUrl: Ignoring inferred base URL "${inferred}" – ${String(
            error,
          )}`,
        );
      }
    }
  }

  return resolveApiBaseUrl(undefined, fallbackUrl);
}

/**
 * Resolve the API base URL for server-side environments (e.g., Next.js RSC).
 *
 * The resolver inspects multiple environment-provided URLs, prioritising the
 * rewrite destination before falling back to the public/SSR URLs.  This mirrors
 * how the frontend is typically configured in production where client and
 * server renders should both target the same backend without requiring
 * duplicate configuration.
 */
export function resolveServerApiBaseUrl({
  rewriteUrl,
  publicUrl,
  ssrUrl,
  fallbackUrl = DEFAULT_CLIENT_API_BASE_URL,
}: {
  /** Direct backend URL used by Next.js rewrite configuration. */
  rewriteUrl?: string | null;
  /** Public-facing API URL exposed to browser bundles. */
  publicUrl?: string | null;
  /** Optional SSR-specific API URL override. */
  ssrUrl?: string | null;
  /** Fallback URL when no environment variables are provided. */
  fallbackUrl?: string;
} = {}): string {
  const candidate = [rewriteUrl, publicUrl, ssrUrl].find(
    (value) => typeof value === "string" && value.trim().length > 0,
  );

  return resolveClientApiBaseUrl(candidate ?? undefined, fallbackUrl);
}

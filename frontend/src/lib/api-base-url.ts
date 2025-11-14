import { resolveApiBaseUrl } from "./resolve-api-base-url";

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
 * Default API base URL for local development.
 * Exported for reuse across modules.
 */
export const DEFAULT_CLIENT_API_BASE_URL = "http://localhost:8000";

/**
 * Ordered list of environment variable names that may define the backend URL
 * when rendering on the server. The sequence mirrors the rewrite configuration
 * logic so that RSC fetches use the same target as Next.js' routing layer.
 */
const SERVER_BASE_URL_ENV_PRIORITY: Array<keyof NodeJS.ProcessEnv> = [
  "NEXT_API_REWRITE_BASE_URL",
  "NEXT_SSR_API_BASE_URL",
  "NEXT_PUBLIC_API_BASE_URL",
];

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
 * Resolve the API base URL for server environments (e.g., Next.js RSC).
 *
 * The server cannot rely on window-based inference, so we check a prioritized
 * set of environment variables that mirror the configuration logic used in
 * `next.config.mjs`. This guarantees that server-rendered API calls honor the
 * same deployment-specific overrides as client-side fetches and Next.js
 * rewrites.
 */
export function resolveServerApiBaseUrl(
  fallbackUrl = DEFAULT_CLIENT_API_BASE_URL,
): string {
  const configuredUrl = SERVER_BASE_URL_ENV_PRIORITY.map(
    (key) => process.env[key],
  ).find((value) => Boolean(value?.trim()));

  return resolveApiBaseUrl(configuredUrl, fallbackUrl);
}

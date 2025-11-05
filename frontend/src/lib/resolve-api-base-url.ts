const SCHEME_REGEX = /^[a-zA-Z][\w+.-]*:\/\//;
const LOCAL_ADDRESS_PREFIXES = ["localhost", "127.", "0.0.0.0", "[::1]"];

function isLikelyLocalAddress(value: string): boolean {
  const lower = value.toLowerCase();
  return LOCAL_ADDRESS_PREFIXES.some((prefix) => lower.startsWith(prefix));
}

function ensureAbsoluteUrl(value: string): string {
  const parsed = new URL(value);
  const normalizedPath =
    parsed.pathname === "/" ? "" : parsed.pathname.replace(/\/$/, "");
  return `${parsed.origin}${normalizedPath}`;
}

export function resolveApiBaseUrl(
  rawUrl: string | undefined,
  fallbackUrl: string
): string {
  let normalizedFallback = fallbackUrl;
  try {
    normalizedFallback = ensureAbsoluteUrl(fallbackUrl);
  } catch (error) {
    // If fallback is ever misconfigured, surface the original error.
    throw new Error(
      `Invalid fallback API base URL "${fallbackUrl}": ${String(error)}`
    );
  }

  const trimmed = rawUrl?.trim();
  if (!trimmed) {
    return normalizedFallback;
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

  if (typeof console !== "undefined") {
    console.warn(
      `resolveApiBaseUrl: invalid API base URL "${trimmed}", falling back to "${normalizedFallback}".`
    );
  }

  return normalizedFallback;
}

import { clsx, type ClassValue } from "clsx";

/**
 * Utility for composing conditional Tailwind class strings.
 * Mirrors the helper shipped with the ShadCN UI starter.
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/**
 * Builds an absolute image URL that works whether the API returned an absolute
 * path or a relative asset reference.
 */
export function resolveImageUrl(path?: string | null) {
  if (!path) {
    return null;
  }

  if (/^(?:[a-z]+:)?\/\//i.test(path) || path.startsWith("data:")) {
    return path;
  }

  const base =
    process.env.NEXT_PUBLIC_ASSETS_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000";

  const normalizedBase = base.replace(/\/+$/, "");
  const normalizedPath = path.replace(/^\/+/, "");

  return `${normalizedBase}/${normalizedPath}`;
}

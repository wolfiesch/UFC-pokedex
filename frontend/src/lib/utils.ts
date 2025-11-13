import { clsx, type ClassValue } from "clsx";

/**
 * Utility for composing conditional Tailwind class strings.
 * Mirrors the helper shipped with the ShadCN UI starter.
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/**
 * Derives readable initials from a fighter name.
 */
export function getInitials(name: string) {
  if (!name) {
    return "";
  }

  const parts = name.trim().split(/\s+/).filter(Boolean);

  if (parts.length === 0) {
    return "";
  }

  if (parts.length === 1) {
    return parts[0]!.slice(0, 2).toUpperCase();
  }

  const first = parts[0]![0] ?? "";
  const last = parts[parts.length - 1]![0] ?? "";

  return `${first}${last}`.toUpperCase();
}

/**
 * Maps a string to a deterministic Tailwind background + border combo.
 */
const COLOR_CLASSES = [
  "bg-blue-500/90 border-blue-500/50",
  "bg-purple-500/90 border-purple-500/50",
  "bg-amber-500/90 border-amber-500/50",
  "bg-emerald-500/90 border-emerald-500/50",
  "bg-rose-500/90 border-rose-500/50",
  "bg-sky-500/90 border-sky-500/50",
  "bg-indigo-500/90 border-indigo-500/50",
  "bg-orange-500/90 border-orange-500/50",
] as const;
const COLOR_CLASS_CACHE = new Map<string, string>();

export function getColorFromString(str: string) {
  const CACHE_LIMIT = 512;
  const cacheKey = str?.toLowerCase() ?? "";
  const cached = COLOR_CLASS_CACHE.get(cacheKey);
  if (cached) {
    return cached;
  }

  if (!str) {
    COLOR_CLASS_CACHE.set(cacheKey, COLOR_CLASSES[0]);
    return COLOR_CLASSES[0];
  }

  let hash = 0;
  for (let i = 0; i < str.length; i += 1) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0; // Convert to 32bit integer
  }

  const colorIndex = Math.abs(hash) % COLOR_CLASSES.length;
  const computed = COLOR_CLASSES[colorIndex];

  if (COLOR_CLASS_CACHE.size >= CACHE_LIMIT) {
    const oldestKey = COLOR_CLASS_CACHE.keys().next().value;
    COLOR_CLASS_CACHE.delete(oldestKey);
  }

  COLOR_CLASS_CACHE.set(cacheKey, computed);
  return computed;
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

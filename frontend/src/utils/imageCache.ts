/**
 * @fileoverview Lightweight LRU cache for decoded opponent headshot ImageBitmaps.
 * The cache intentionally caps entries to avoid ballooning GPU memory usage while
 * still keeping enough thumbnails warm for buttery-smooth scatter plot interactions.
 */

/** Maximum number of ImageBitmap objects retained in-memory concurrently. */
const MAX_CACHE_SIZE = 256;

/** Internal backing store maintaining insertion order for LRU semantics. */
const bitmapCache: Map<string, ImageBitmap> = new Map();

/** Tracks ongoing fetch/decoding operations to coalesce concurrent callers. */
const inflightDecodes: Map<string, Promise<ImageBitmap>> = new Map();

/**
 * Evicts the least-recently-used ImageBitmap when the cache grows beyond capacity.
 */
const trimCache = (): void => {
  if (bitmapCache.size <= MAX_CACHE_SIZE) {
    return;
  }
  const oldestKey = bitmapCache.keys().next().value as string | undefined;
  if (oldestKey) {
    const bitmap = bitmapCache.get(oldestKey);
    if (bitmap) {
      bitmap.close?.();
    }
    bitmapCache.delete(oldestKey);
  }
};

/**
 * Fetches a remote image resource and decodes it into an ImageBitmap off the main thread.
 * @param url Absolute or relative URL to the opponent headshot asset.
 */
export const loadBitmap = async (url: string): Promise<ImageBitmap> => {
  const response = await fetch(url, {
    credentials: 'omit',
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch image at ${url}: ${response.status}`);
  }
  const blob = await response.blob();
  return createImageBitmap(blob);
};

/**
 * Retrieves (and caches) an opponent headshot keyed by the stable opponent identifier.
 * @param opponentId Canonical identifier used to deduplicate cache entries.
 * @param url Source URL to fetch when the bitmap is not yet available.
 */
export const getOpponentBitmap = async (
  opponentId: string,
  url: string,
): Promise<ImageBitmap> => {
  const cacheKey = opponentId ?? url;
  const cachedBitmap = bitmapCache.get(cacheKey);
  if (cachedBitmap) {
    // Move to the tail of the map to mark as recently used.
    bitmapCache.delete(cacheKey);
    bitmapCache.set(cacheKey, cachedBitmap);
    return cachedBitmap;
  }

  const existingDecode = inflightDecodes.get(cacheKey);
  if (existingDecode) {
    return existingDecode;
  }

  const decodePromise = loadBitmap(url)
    .then((bitmap) => {
      inflightDecodes.delete(cacheKey);
      bitmapCache.set(cacheKey, bitmap);
      trimCache();
      return bitmap;
    })
    .catch((error) => {
      inflightDecodes.delete(cacheKey);
      throw error;
    });

  inflightDecodes.set(cacheKey, decodePromise);
  return decodePromise;
};

/**
 * Clears all cached ImageBitmap instances. Primarily exposed for deterministic tests.
 */
export const resetImageCache = (): void => {
  bitmapCache.forEach((bitmap) => bitmap.close?.());
  bitmapCache.clear();
  inflightDecodes.clear();
};

export type { ImageBitmap };

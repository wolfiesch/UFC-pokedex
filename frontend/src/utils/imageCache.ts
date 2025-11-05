const MAX_CACHE_ENTRIES = 256;

export type IdleCallbackHandle = number | ReturnType<typeof setTimeout>;

/**
 * Gracefully handles browsers without `requestIdleCallback` support by
 * delegating to `setTimeout`. The signature matches the native implementation.
 */
export const requestIdleCallbackShim = (
  callback: IdleRequestCallback,
  options?: IdleRequestOptions,
): IdleCallbackHandle => {
  if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
    return (window.requestIdleCallback as typeof requestIdleCallback)(callback, options);
  }

  return setTimeout(() => {
    callback({
      didTimeout: false,
      timeRemaining: () => 0,
    });
  }, options?.timeout ?? 16);
};

/**
 * Cancels an idle callback regardless of the platform-native implementation.
 */
export const cancelIdleCallbackShim = (handle: IdleCallbackHandle) => {
  if (typeof window !== 'undefined' && 'cancelIdleCallback' in window) {
    (window.cancelIdleCallback as typeof cancelIdleCallback)(handle);
    return;
  }

  clearTimeout(handle);
};

/** Internal cache map maintaining least-recently-used semantics. */
const bitmapCache: Map<string, ImageBitmap> = new Map();
/** Tracks in-flight fetch operations to avoid duplicate downloads. */
const pendingFetches: Map<string, Promise<ImageBitmap>> = new Map();

/**
 * Loads an `ImageBitmap` by fetching the remote resource and decoding it off
 * the main thread. Consumers should rarely call this directly; prefer the
 * cached `getOpponentBitmap` helper.
 */
export const loadBitmap = async (url: string): Promise<ImageBitmap> => {
  const response = await fetch(url, { cache: 'force-cache' });
  if (!response.ok) {
    throw new Error(`Failed to load headshot: ${response.status} ${response.statusText}`);
  }
  const blob = await response.blob();
  return createImageBitmap(blob);
};

/**
 * Fetches or reuses an opponent headshot bitmap. The cache is keyed by the
 * opponent id so that identical thumbnails referenced by different fights are
 * only decoded once.
 */
export const getOpponentBitmap = async (
  opponentId: string,
  url: string,
): Promise<ImageBitmap> => {
  const cacheKey = opponentId;
  const cached = bitmapCache.get(cacheKey);
  if (cached) {
    // Refresh the recency ordering by reinserting the bitmap.
    bitmapCache.delete(cacheKey);
    bitmapCache.set(cacheKey, cached);
    return cached;
  }

  const pending = pendingFetches.get(cacheKey);
  if (pending) {
    return pending;
  }

  const loadPromise = loadBitmap(url)
    .then((bitmap) => {
      pendingFetches.delete(cacheKey);

      if (bitmapCache.size >= MAX_CACHE_ENTRIES) {
        const oldestKey = bitmapCache.keys().next().value as string | undefined;
        if (oldestKey) {
          const oldest = bitmapCache.get(oldestKey);
          bitmapCache.delete(oldestKey);
          oldest?.close();
        }
      }

      bitmapCache.set(cacheKey, bitmap);
      return bitmap;
    })
    .catch((error) => {
      pendingFetches.delete(cacheKey);
      throw error;
    });

  pendingFetches.set(cacheKey, loadPromise);
  return loadPromise;
};

/**
 * Allows tests to clear the bitmap cache between runs.
 */
export const __resetBitmapCache = () => {
  bitmapCache.forEach((bitmap) => bitmap.close());
  bitmapCache.clear();
  pendingFetches.clear();
};

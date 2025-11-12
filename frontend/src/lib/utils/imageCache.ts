/**
 * LRU Image Cache for efficient ImageBitmap management
 * Provides off-thread image decoding and caching with automatic eviction
 * Supports intelligent face detection for circular crops
 */

import { detectSubjectCenter } from "./faceDetection";

/**
 * Cache entry with LRU tracking
 */
interface CacheEntry {
  bitmap: ImageBitmap;
  lastAccessed: number;
}

/**
 * LRU Cache for ImageBitmap objects
 * Implements Least Recently Used eviction policy
 */
class ImageBitmapCache {
  private cache: Map<string, CacheEntry> = new Map();
  private maxSize: number;
  private loadingUrls: Set<string> = new Set();
  private placeholderBitmap: ImageBitmap | null = null;

  constructor(maxSize: number = 256) {
    this.maxSize = maxSize;
    this.initPlaceholder();
  }

  /**
   * Creates a placeholder ImageBitmap for missing/loading images
   */
  private async initPlaceholder(): Promise<void> {
    try {
      // Create a 32x32 gray circle as placeholder
      const canvas = document.createElement("canvas");
      canvas.width = 32;
      canvas.height = 32;
      const ctx = canvas.getContext("2d");

      if (ctx) {
        // Draw gray circle
        ctx.fillStyle = "#95a5a6";
        ctx.beginPath();
        ctx.arc(16, 16, 15, 0, Math.PI * 2);
        ctx.fill();
      }

      const blob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob(resolve);
      });

      if (blob) {
        this.placeholderBitmap = await createImageBitmap(blob);
      }
    } catch (error) {
      console.warn("Failed to create placeholder bitmap:", error);
    }
  }

  /**
   * Creates an initials-based placeholder ImageBitmap
   * @param name - Full name to extract initials from
   * @returns ImageBitmap with colored circle and initials
   */
  private async createInitialsPlaceholder(name: string): Promise<ImageBitmap | null> {
    try {
      const canvas = document.createElement("canvas");
      canvas.width = 32;
      canvas.height = 32;
      const ctx = canvas.getContext("2d");

      if (!ctx) return this.placeholderBitmap;

      // Generate color from name hash
      const hash = name.split('').reduce((acc, char) => {
        return char.charCodeAt(0) + ((acc << 5) - acc);
      }, 0);
      const hue = Math.abs(hash) % 360;
      const color = `hsl(${hue}, 65%, 50%)`;

      // Draw colored circle
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(16, 16, 15, 0, Math.PI * 2);
      ctx.fill();

      // Extract initials (first letter of first and last name)
      const parts = name.trim().split(/\s+/);
      let initials = "";
      if (parts.length >= 2) {
        initials = parts[0][0] + parts[parts.length - 1][0];
      } else if (parts.length === 1) {
        initials = parts[0].substring(0, 2);
      }
      initials = initials.toUpperCase();

      // Draw initials
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 12px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(initials, 16, 16);

      const blob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob(resolve);
      });

      if (blob) {
        return await createImageBitmap(blob);
      }
      return this.placeholderBitmap;
    } catch (error) {
      console.warn("Failed to create initials placeholder:", error);
      return this.placeholderBitmap;
    }
  }

  /**
   * Gets an ImageBitmap from cache or returns placeholder
   */
  get(url: string): ImageBitmap | null {
    const entry = this.cache.get(url);
    if (entry) {
      entry.lastAccessed = Date.now();
      return entry.bitmap;
    }
    return this.placeholderBitmap;
  }

  /**
   * Sets an ImageBitmap in cache with LRU eviction if needed
   */
  private set(url: string, bitmap: ImageBitmap): void {
    // If cache is full, evict least recently used
    if (this.cache.size >= this.maxSize) {
      this.evictLRU();
    }

    this.cache.set(url, {
      bitmap,
      lastAccessed: Date.now(),
    });
  }

  /**
   * Evicts the least recently used entry
   */
  private evictLRU(): void {
    let oldestUrl: string | null = null;
    let oldestTime = Infinity;

    for (const [url, entry] of this.cache.entries()) {
      if (entry.lastAccessed < oldestTime) {
        oldestTime = entry.lastAccessed;
        oldestUrl = url;
      }
    }

    if (oldestUrl) {
      const entry = this.cache.get(oldestUrl);
      if (entry) {
        // Close the bitmap to free memory
        entry.bitmap.close();
        this.cache.delete(oldestUrl);
      }
    }
  }

  /**
   * Checks if URL is cached
   */
  has(url: string): boolean {
    return this.cache.has(url);
  }

  /**
   * Checks if URL is currently being loaded
   */
  isLoading(url: string): boolean {
    return this.loadingUrls.has(url);
  }

  /**
   * Creates a circular crop of an image with smart face detection
   * @param bitmap - Source ImageBitmap to crop
   * @param size - Diameter of circular crop
   * @param detectFace - Whether to use face detection for centering
   * @returns Circular cropped ImageBitmap
   */
  private async createCircularCrop(
    bitmap: ImageBitmap,
    size: number = 40,
    detectFace: boolean = true
  ): Promise<ImageBitmap | null> {
    try {
      const canvas = document.createElement("canvas");
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext("2d");

      if (!ctx) return null;

      // Detect subject center if requested
      let centerX = 0.5;
      let centerY = 0.5;

      if (detectFace) {
        try {
          // Extract ImageData from bitmap for analysis
          const tempCanvas = document.createElement("canvas");
          tempCanvas.width = bitmap.width;
          tempCanvas.height = bitmap.height;
          const tempCtx = tempCanvas.getContext("2d");

          if (tempCtx) {
            tempCtx.drawImage(bitmap, 0, 0);
            const imageData = tempCtx.getImageData(
              0,
              0,
              bitmap.width,
              bitmap.height
            );
            const center = detectSubjectCenter(imageData);
            centerX = center.x;
            centerY = center.y;
          }
        } catch (error) {
          console.warn("Face detection failed, using center crop:", error);
        }
      }

      // Calculate crop region
      const sourceSize = Math.min(bitmap.width, bitmap.height);
      const sourceX = centerX * bitmap.width - sourceSize / 2;
      const sourceY = centerY * bitmap.height - sourceSize / 2;

      // Ensure crop stays within bounds
      const clampedSourceX = Math.max(
        0,
        Math.min(sourceX, bitmap.width - sourceSize)
      );
      const clampedSourceY = Math.max(
        0,
        Math.min(sourceY, bitmap.height - sourceSize)
      );

      // Create circular clip
      ctx.save();
      ctx.beginPath();
      ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
      ctx.clip();

      // Draw cropped image
      ctx.drawImage(
        bitmap,
        clampedSourceX,
        clampedSourceY,
        sourceSize,
        sourceSize,
        0,
        0,
        size,
        size
      );

      ctx.restore();

      // Convert to ImageBitmap
      const blob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob(resolve);
      });

      if (blob) {
        return await createImageBitmap(blob);
      }

      return null;
    } catch (error) {
      console.warn("Failed to create circular crop:", error);
      return null;
    }
  }

  /**
   * Loads an ImageBitmap from URL with off-thread decoding
   */
  async loadBitmap(url: string): Promise<ImageBitmap | null> {
    // Check cache first
    if (this.cache.has(url)) {
      return this.get(url);
    }

    // Avoid duplicate requests
    if (this.loadingUrls.has(url)) {
      return this.placeholderBitmap;
    }

    this.loadingUrls.add(url);

    try {
      // Fetch and decode image off the main thread
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch image: ${response.statusText}`);
      }

      const blob = await response.blob();
      const bitmap = await createImageBitmap(blob);

      // Cache the result
      this.set(url, bitmap);
      return bitmap;
    } catch (error) {
      console.warn(`Failed to load bitmap from ${url}:`, error);
      return this.placeholderBitmap;
    } finally {
      this.loadingUrls.delete(url);
    }
  }

  /**
   * Loads a bitmap with smart circular cropping
   * @param url - URL of the image
   * @param size - Diameter of circular crop (default: 40)
   * @param detectFace - Whether to use face detection (default: true)
   * @returns Circular cropped ImageBitmap
   */
  async loadBitmapWithCrop(
    url: string,
    size: number = 40,
    detectFace: boolean = true
  ): Promise<ImageBitmap | null> {
    const cacheKey = `${url}:crop:${size}:${detectFace}`;

    // Check cache first
    if (this.cache.has(cacheKey)) {
      return this.get(cacheKey);
    }

    // Load original bitmap
    const originalBitmap = await this.loadBitmap(url);
    if (!originalBitmap || originalBitmap === this.placeholderBitmap) {
      return originalBitmap;
    }

    // Create circular crop
    const croppedBitmap = await this.createCircularCrop(
      originalBitmap,
      size,
      detectFace
    );

    if (croppedBitmap) {
      // Cache the cropped version
      this.set(cacheKey, croppedBitmap);
      return croppedBitmap;
    }

    // Fallback to original bitmap
    return originalBitmap;
  }

  /**
   * Gets opponent bitmap by ID, loading if not cached
   * Falls back to initials-based placeholder if image not found
   */
  async getOpponentBitmap(
    opponentId: string,
    url: string | null,
    opponentName?: string
  ): Promise<ImageBitmap | null> {
    const imageUrl = url || `/img/opponents/${opponentId}-32.webp`;

    // Try to load the image
    const bitmap = await this.loadBitmap(imageUrl);

    // If image loaded successfully, return it
    if (bitmap && bitmap !== this.placeholderBitmap) {
      return bitmap;
    }

    // If we have opponent name, create and cache initials placeholder
    if (opponentName) {
      const placeholderKey = `placeholder:${opponentId}`;

      // Check if we already have this initials placeholder cached
      if (this.has(placeholderKey)) {
        return this.get(placeholderKey);
      }

      // Create new initials placeholder
      const initialsPlaceholder = await this.createInitialsPlaceholder(opponentName);
      if (initialsPlaceholder && initialsPlaceholder !== this.placeholderBitmap) {
        // Cache it with a special key
        this.set(placeholderKey, initialsPlaceholder);
        return initialsPlaceholder;
      }
    }

    // Fall back to generic placeholder
    return this.placeholderBitmap;
  }

  /**
   * Preloads multiple bitmaps in the background
   * Uses requestIdleCallback for low-priority loading
   * Returns a cancel function to stop preloading
   */
  preloadBitmaps(urls: string[]): () => void {
    let cancelled = false;
    const timeoutIds: number[] = [];
    const idleCallbackIds: number[] = [];

    const cleanup = () => {
      cancelled = true;
      timeoutIds.forEach(id => clearTimeout(id));
      idleCallbackIds.forEach(id => {
        if ('cancelIdleCallback' in window) {
          (window as any).cancelIdleCallback(id);
        }
      });
      timeoutIds.length = 0;
      idleCallbackIds.length = 0;
    };

    const loadNext = (index: number) => {
      // Stop if cancelled or reached end
      if (cancelled || index >= urls.length) {
        cleanup();
        return;
      }

      const url = urls[index];
      if (!this.has(url) && !this.isLoading(url)) {
        this.loadBitmap(url).then(() => {
          if (cancelled) return;

          // Schedule next load
          if ("requestIdleCallback" in window) {
            const id = requestIdleCallback(() => loadNext(index + 1));
            idleCallbackIds.push(id);
          } else {
            const id = setTimeout(() => loadNext(index + 1), 16) as unknown as number;
            timeoutIds.push(id);
          }
        });
      } else {
        // Skip already cached/loading images
        if (cancelled) return;

        if ("requestIdleCallback" in window) {
          const id = requestIdleCallback(() => loadNext(index + 1));
          idleCallbackIds.push(id);
        } else {
          const id = setTimeout(() => loadNext(index + 1), 16) as unknown as number;
          timeoutIds.push(id);
        }
      }
    };

    // Start loading
    if ("requestIdleCallback" in window) {
      const id = requestIdleCallback(() => loadNext(0));
      idleCallbackIds.push(id);
    } else {
      const id = setTimeout(() => loadNext(0), 100) as unknown as number;
      timeoutIds.push(id);
    }

    // Return cleanup function
    return cleanup;
  }

  /**
   * Clears the entire cache and closes all bitmaps
   */
  clear(): void {
    for (const entry of this.cache.values()) {
      entry.bitmap.close();
    }
    this.cache.clear();
    this.loadingUrls.clear();

    if (this.placeholderBitmap) {
      this.placeholderBitmap.close();
      this.placeholderBitmap = null;
      this.initPlaceholder();
    }
  }

  /**
   * Gets cache statistics
   */
  getStats(): {
    size: number;
    maxSize: number;
    loading: number;
  } {
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      loading: this.loadingUrls.size,
    };
  }
}

// Export singleton instance
export const imageCache = new ImageBitmapCache(256);

/**
 * Convenience function to load a bitmap
 */
export async function loadBitmap(url: string): Promise<ImageBitmap | null> {
  return imageCache.loadBitmap(url);
}

/**
 * Convenience function to get opponent bitmap
 */
export async function getOpponentBitmap(
  opponentId: string,
  url: string | null = null,
  opponentName?: string
): Promise<ImageBitmap | null> {
  return imageCache.getOpponentBitmap(opponentId, url, opponentName);
}

/**
 * Convenience function to preload bitmaps
 * Returns a cancel function to stop preloading
 */
export function preloadBitmaps(urls: string[]): () => void {
  return imageCache.preloadBitmaps(urls);
}

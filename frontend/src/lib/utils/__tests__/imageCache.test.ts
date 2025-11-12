import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { preloadBitmaps } from '../imageCache';

describe('preloadBitmaps', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('should allow cancellation of preload operation', () => {
    const urls = [
      'https://example.com/image1.jpg',
      'https://example.com/image2.jpg',
      'https://example.com/image3.jpg',
    ];

    // Start preload and get cancellation function
    const cancel = preloadBitmaps(urls);

    // Cancel immediately
    cancel();

    // Fast-forward timers - no images should be loaded after cancellation
    vi.advanceTimersByTime(1000);

    // Verify no image loading occurred (this will fail until we implement cancellation)
    expect(document.querySelectorAll('img[data-preload]').length).toBe(0);
  });

  it('should clean up when preload completes naturally', async () => {
    const urls = ['https://example.com/image1.jpg'];

    const cancel = preloadBitmaps(urls);

    // Let it complete
    await vi.runAllTimersAsync();

    // Should not throw when called after completion
    expect(() => cancel()).not.toThrow();
  });
});

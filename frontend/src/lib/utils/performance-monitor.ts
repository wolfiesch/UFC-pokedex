/**
 * Real-world performance monitoring utility
 * Tracks actual user-facing metrics, not static analysis
 */

interface PerformanceMetric {
  name: string;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  timestamp: number;
}

const metrics: PerformanceMetric[] = [];
let memoryIntervalId: number | null = null;

/**
 * Track Core Web Vitals
 */
export function initPerformanceMonitoring() {
  if (typeof window === 'undefined') return;

  // Track Largest Contentful Paint (LCP)
  if ('PerformanceObserver' in window) {
    try {
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1];

        const lcp = lastEntry.startTime;
        const rating = lcp < 2500 ? 'good' : lcp < 4000 ? 'needs-improvement' : 'poor';

        logMetric({
          name: 'LCP',
          value: lcp,
          rating,
          timestamp: Date.now(),
        });
      });

      lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
    } catch (e) {
      // PerformanceObserver not supported
    }

    // Track First Input Delay (FID)
    try {
      const fidObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry: any) => {
          const fid = entry.processingStart - entry.startTime;
          const rating = fid < 100 ? 'good' : fid < 300 ? 'needs-improvement' : 'poor';

          logMetric({
            name: 'FID',
            value: fid,
            rating,
            timestamp: Date.now(),
          });
        });
      });

      fidObserver.observe({ entryTypes: ['first-input'] });
    } catch (e) {
      // Not supported
    }

    // Track Cumulative Layout Shift (CLS)
    try {
      let clsValue = 0;
      const clsObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry: any) => {
          if (!entry.hadRecentInput) {
            clsValue += entry.value;
          }
        });

        const rating = clsValue < 0.1 ? 'good' : clsValue < 0.25 ? 'needs-improvement' : 'poor';

        logMetric({
          name: 'CLS',
          value: clsValue,
          rating,
          timestamp: Date.now(),
        });
      });

      clsObserver.observe({ entryTypes: ['layout-shift'] });
    } catch (e) {
      // Not supported
    }
  }

  // Track memory usage (if available)
  // Clear existing interval before creating new one
  if (memoryIntervalId !== null) {
    clearInterval(memoryIntervalId);
  }

  if ('memory' in performance) {
    memoryIntervalId = setInterval(() => {
      const mem = (performance as any).memory;
      const usedMB = mem.usedJSHeapSize / 1048576;
      const totalMB = mem.totalJSHeapSize / 1048576;
      const limitMB = mem.jsHeapSizeLimit / 1048576;

      const usage = (usedMB / limitMB) * 100;
      const rating = usage < 50 ? 'good' : usage < 75 ? 'needs-improvement' : 'poor';

      logMetric({
        name: 'Memory',
        value: usedMB,
        rating,
        timestamp: Date.now(),
      });

      if (rating === 'poor') {
        console.warn(`High memory usage: ${usedMB.toFixed(2)}MB / ${totalMB.toFixed(2)}MB`);
      }
    }, 30000) as unknown as number; // Check every 30 seconds
  }
}

function logMetric(metric: PerformanceMetric) {
  metrics.push(metric);

  // Keep only last 100 metrics
  if (metrics.length > 100) {
    metrics.shift();
  }

  // Log to console in development
  if (process.env.NODE_ENV === 'development') {
    const emoji = metric.rating === 'good' ? '✅' : metric.rating === 'needs-improvement' ? '⚠️' : '❌';
    console.log(`${emoji} ${metric.name}: ${metric.value.toFixed(2)}ms (${metric.rating})`);
  }

  // TODO: Send to analytics in production
}

/**
 * Get performance summary
 */
export function getPerformanceMetrics(): PerformanceMetric[] {
  return [...metrics];
}

/**
 * Measure custom operation
 */
export function measureOperation<T>(name: string, operation: () => T): T {
  const start = performance.now();
  const result = operation();
  const duration = performance.now() - start;

  const rating = duration < 16 ? 'good' : duration < 50 ? 'needs-improvement' : 'poor';

  logMetric({
    name: `Custom: ${name}`,
    value: duration,
    rating,
    timestamp: Date.now(),
  });

  return result;
}

/**
 * Measure async operation
 */
export async function measureAsyncOperation<T>(
  name: string,
  operation: () => Promise<T>
): Promise<T> {
  const start = performance.now();
  const result = await operation();
  const duration = performance.now() - start;

  const rating = duration < 100 ? 'good' : duration < 500 ? 'needs-improvement' : 'poor';

  logMetric({
    name: `Async: ${name}`,
    value: duration,
    rating,
    timestamp: Date.now(),
  });

  return result;
}

/**
 * Clean up performance monitoring (call on unmount if needed)
 */
export function cleanupPerformanceMonitoring() {
  if (memoryIntervalId !== null) {
    clearInterval(memoryIntervalId);
    memoryIntervalId = null;
  }
}

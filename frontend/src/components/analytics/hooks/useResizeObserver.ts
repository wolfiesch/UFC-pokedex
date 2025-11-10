import { useEffect, useState } from "react";

import type { ScatterDimensions } from "./useFightScatterState";

interface UseResizeObserverOptions {
  /** Ref callback target whose bounding box we measure. */
  element: HTMLElement | null;
  /** Fixed height for the chart; width remains responsive. */
  height: number;
  /** Default width to fall back to before the observer fires. */
  fallbackWidth?: number;
}

/**
 * Watches a container element and exposes the latest width. The chart height is
 * externally controlled, so the hook simply echoes it for convenience.
 */
export function useResizeObserver({
  element,
  height,
  fallbackWidth = 800,
}: UseResizeObserverOptions): ScatterDimensions {
  const [dimensions, setDimensions] = useState<ScatterDimensions>({
    width: fallbackWidth,
    height,
  });

  useEffect(() => {
    if (!element) {
      return;
    }

    const updateDimensions = () => {
      const nextWidth = element.getBoundingClientRect().width;
      setDimensions({ width: nextWidth, height });
    };

    updateDimensions();

    const resizeObserver = new ResizeObserver(() => {
      updateDimensions();
    });

    resizeObserver.observe(element);

    return () => {
      resizeObserver.disconnect();
    };
  }, [element, height]);

  useEffect(() => {
    setDimensions((current) => ({ ...current, height }));
  }, [height]);

  return dimensions;
}

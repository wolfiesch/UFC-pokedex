import { useEffect } from "react";
import { select } from "d3-selection";
import { zoom as d3Zoom, type D3ZoomEvent } from "d3-zoom";

import type { Transform } from "@/types/fight-scatter";

interface UseZoomTransformOptions {
  overlay: SVGSVGElement | null;
  extent: [number, number];
  onTransform: (transform: Transform) => void;
}

/**
 * Bridges d3-zoom with React state, ensuring the imperative bindings are
 * encapsulated and reliably cleaned up when the overlay or dependencies change.
 */
export function useZoomTransform({
  overlay,
  extent,
  onTransform,
}: UseZoomTransformOptions): void {
  useEffect(() => {
    if (!overlay) {
      return;
    }

    const zoomBehavior = d3Zoom<SVGSVGElement, unknown>()
      .scaleExtent(extent)
      .on("zoom", (event: D3ZoomEvent<SVGSVGElement, unknown>) => {
        const { k, x, y } = event.transform;
        onTransform({ scale: k, translateX: x, translateY: y });
      });

    const selection = select(overlay);
    selection.call(zoomBehavior);

    return () => {
      selection.on(".zoom", null);
    };
  }, [overlay, extent, onTransform]);
}

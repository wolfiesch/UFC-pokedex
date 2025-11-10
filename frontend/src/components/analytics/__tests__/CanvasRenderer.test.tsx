import { render, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { scaleLinear, scaleTime } from "d3-scale";

import type { RenderedFight, ScatterDimensions } from "../hooks/useFightScatterState";
import { CanvasRenderer } from "../CanvasRenderer";
import type { Transform } from "@/types/fight-scatter";

declare global {
  interface HTMLCanvasElement {
    getContext(contextId: "2d"): CanvasRenderingContext2D | null;
  }
}

vi.mock("@/lib/utils/imageCache", () => ({
  imageCache: {
    get: vi.fn(() => null),
  },
}));

const dimensions: ScatterDimensions = { width: 400, height: 300 };
const transform: Transform = { scale: 1, translateX: 0, translateY: 0 };

function createMockContext() {
  return {
    scale: vi.fn(),
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    fillStyle: "",
    beginPath: vi.fn(),
    arc: vi.fn(),
    clip: vi.fn(),
    drawImage: vi.fn(),
    fill: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    strokeStyle: "",
    lineWidth: 0,
    stroke: vi.fn(),
    globalAlpha: 1,
    fillText: vi.fn(),
    font: "",
    textAlign: "",
    textBaseline: "",
    shadowColor: "",
    shadowBlur: 0,
    moveTo: vi.fn(),
    lineTo: vi.fn(),
  } as unknown as CanvasRenderingContext2D;
}

describe("CanvasRenderer", () => {
  beforeEach(() => {
    Object.defineProperty(window, "devicePixelRatio", {
      value: 1,
      configurable: true,
    });
  });

  it("draws hexbins and scatter points", async () => {
    const heatmapCanvas = document.createElement("canvas");
    const pointsCanvas = document.createElement("canvas");
    const heatmapContext = createMockContext();
    const pointsContext = createMockContext();

    heatmapCanvas.getContext = vi.fn().mockReturnValue(heatmapContext);
    pointsCanvas.getContext = vi.fn().mockReturnValue(pointsContext);

    const xScale = scaleTime<number, number>()
      .domain([new Date("2020-01-01"), new Date("2021-01-01")])
      .range([40, dimensions.width - 40]);
    const yScale = scaleLinear<number, number>()
      .domain([400, 0])
      .range([40, dimensions.height - 40]);

    const fights: RenderedFight[] = [
      {
        id: "fight-1",
        date: "2020-06-01T00:00:00.000Z",
        finish_seconds: 180,
        method: "KO",
        result: "W",
        opponent_id: "abc",
        opponent_name: "Alex Example",
        headshot_url: null,
        event_name: "Event",
        screenX: 120,
        screenY: 150,
      },
    ];

    render(
      <CanvasRenderer
        dimensions={dimensions}
        hexbins={[{ i: 0, j: 0, count: 4 }]}
        heatmapCanvas={heatmapCanvas}
        pointsCanvas={pointsCanvas}
        renderedFights={fights}
        filterResults={[]}
        filterMethods={[]}
        showDensity
        showTrend={false}
        trendPoints={[]}
        xScale={xScale}
        yScale={yScale}
        transform={transform}
      />
    );

    await waitFor(() => {
      expect(heatmapContext.fillRect).toHaveBeenCalled();
      expect(pointsContext.arc).toHaveBeenCalled();
      expect(pointsContext.stroke).toHaveBeenCalled();
    });
  });
});

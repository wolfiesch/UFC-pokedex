import { render, waitFor } from "@testing-library/react";
import { describe, expect, it, beforeAll, afterAll, vi } from "vitest";

import type { TrendPoint } from "@/types/fight-scatter";

import { TrendWorkerProvider } from "../TrendWorkerProvider";

declare global {
  // eslint-disable-next-line no-var
  var Worker: typeof Worker | undefined;
}

class MockWorker {
  private listeners = new Map<string, Set<(event: MessageEvent) => void>>();

  constructor(url: URL) {
    void url;
  }

  postMessage(data: unknown) {
    const listeners = this.listeners.get("message");
    if (!listeners) return;
    const payload = data as { points: TrendPoint[] };
    const event = { data: { type: "result", points: payload.points } } as MessageEvent;
    listeners.forEach((listener) => listener(event));
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)?.add(listener);
  }

  removeEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners.get(type)?.delete(listener);
  }

  terminate() {
    this.listeners.clear();
  }
}

describe("TrendWorkerProvider", () => {
  let originalWorker: typeof Worker | undefined;

  beforeAll(() => {
    originalWorker = globalThis.Worker;
    // @ts-expect-error - assigning mock worker for tests
    globalThis.Worker = MockWorker as unknown as typeof Worker;
  });

  afterAll(() => {
    globalThis.Worker = originalWorker;
  });

  it("exposes worker-computed trend points", async () => {
    const samplePoints: TrendPoint[] = [
      { x: Date.now(), y: 120 },
      { x: Date.now() + 10_000, y: 300 },
    ];
    const spy = vi.fn();

    render(
      <TrendWorkerProvider enabled points={samplePoints}>
        {({ trendPoints }) => {
          spy(trendPoints);
          return null;
        }}
      </TrendWorkerProvider>
    );

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith(samplePoints);
    });
  });
});

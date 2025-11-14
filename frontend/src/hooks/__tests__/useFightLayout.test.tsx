import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useFightLayout } from "../useFightLayout";

const sampleGraph = {
  nodes: [
    {
      fighter_id: "ufc-100",
      name: "Alpha",
      division: "Lightweight",
      record: "10-2-0",
      image_url: null,
      total_fights: 12,
      latest_event_date: "2024-01-01",
    },
    {
      fighter_id: "ufc-200",
      name: "Bravo",
      division: "Featherweight",
      record: "8-3-0",
      image_url: null,
      total_fights: 9,
      latest_event_date: "2023-02-02",
    },
  ],
  links: [
    {
      source: "ufc-100",
      target: "ufc-200",
      fights: 1,
      first_event_name: "Test Event",
      first_event_date: "2022-05-01",
      last_event_name: "Test Event",
      last_event_date: "2022-05-01",
      result_breakdown: {
        "ufc-100": { win: 1 },
        "ufc-200": { loss: 1 },
      },
    },
  ],
  metadata: {},
} as const;

describe("useFightLayout", () => {
  const originalWorker = globalThis.Worker;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    if (originalWorker) {
      globalThis.Worker = originalWorker;
    } else {
      // @ts-expect-error - delete restores test environment Worker when absent
      delete globalThis.Worker;
    }
  });

  it("switches to fallback layout mode when the Worker constructor throws", async () => {
    class ThrowingWorker {
      constructor() {
        throw new Error("Worker not supported");
      }
    }

    globalThis.Worker = ThrowingWorker as unknown as typeof Worker;

    const { result } = renderHook(() => useFightLayout(sampleGraph));

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(result.current.layoutState.mode).toBe("fallback");
    expect(result.current.nodes).toHaveLength(sampleGraph.nodes.length);
    expect(result.current.links).toHaveLength(sampleGraph.links.length);
  });
});

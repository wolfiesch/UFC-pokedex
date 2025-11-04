import { describe, expect, it } from "vitest";

import type { FightGraphResponse } from "@/lib/types";

import {
  computeForceLayout,
  createDivisionColorScale,
  deriveEventYearBounds,
} from "../graph-layout";

const sampleGraph: FightGraphResponse = {
  nodes: [
    {
      fighter_id: "alpha",
      name: "Alpha",
      division: "Featherweight",
      record: "10-2-0",
      image_url: null,
      total_fights: 12,
      latest_event_date: "2024-03-01",
    },
    {
      fighter_id: "bravo",
      name: "Bravo",
      division: "Lightweight",
      record: "8-3-0",
      image_url: null,
      total_fights: 9,
      latest_event_date: "2023-11-12",
    },
    {
      fighter_id: "charlie",
      name: "Charlie",
      division: "Featherweight",
      record: "12-4-0",
      image_url: null,
      total_fights: 15,
      latest_event_date: "2022-05-10",
    },
  ],
  links: [
    {
      source: "alpha",
      target: "bravo",
      fights: 2,
      first_event_name: "Event A",
      first_event_date: "2019-06-01",
      last_event_name: "Event B",
      last_event_date: "2024-03-01",
      result_breakdown: {
        alpha: { win: 1, loss: 1 },
        bravo: { win: 1, loss: 1 },
      },
    },
    {
      source: "alpha",
      target: "charlie",
      fights: 1,
      first_event_name: "Event C",
      first_event_date: "2018-02-12",
      last_event_name: "Event C",
      last_event_date: "2018-02-12",
      result_breakdown: {
        alpha: { win: 1 },
        charlie: { loss: 1 },
      },
    },
  ],
  metadata: {
    event_window: {
      start: "2018-02-12",
      end: "2024-03-01",
    },
  },
};

describe("graph-layout utilities", () => {
  it("computes a layout with finite node positions", () => {
    const layout = computeForceLayout(sampleGraph.nodes, sampleGraph.links, {
      iterations: 80,
    });

    expect(layout.nodes).toHaveLength(sampleGraph.nodes.length);
    layout.nodes.forEach((node) => {
      expect(Number.isFinite(node.x)).toBe(true);
      expect(Number.isFinite(node.y)).toBe(true);
      expect(node.neighbors.length).toBeGreaterThanOrEqual(0);
    });
    expect(layout.edges).toHaveLength(sampleGraph.links.length);
  });

  it("builds a stable color palette for divisions", () => {
    const palette = createDivisionColorScale(sampleGraph.nodes);
    expect(palette.size).toBe(2);
    expect(palette.get("Featherweight")).toBeDefined();
    expect(palette.get("Lightweight")).toBeDefined();
  });

  it("derives event year bounds from metadata when available", () => {
    const bounds = deriveEventYearBounds(sampleGraph);
    expect(bounds).toEqual({ min: 2018, max: 2024 });
  });

  it("falls back to link data when metadata window is absent", () => {
    const withoutMetadata: FightGraphResponse = {
      ...sampleGraph,
      metadata: {},
    };
    const bounds = deriveEventYearBounds(withoutMetadata);
    expect(bounds).toEqual({ min: 2018, max: 2024 });
  });
});

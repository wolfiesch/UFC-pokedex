import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ScatterFight, Transform } from "@/types/fight-scatter";

import { useFightScatterState } from "../hooks/useFightScatterState";

const SAMPLE_FIGHTS: ScatterFight[] = [
  {
    id: "fight-1",
    date: "2020-01-01T00:00:00.000Z",
    finish_seconds: 300,
    method: "DEC",
    result: "W",
    opponent_id: "opp-1",
    opponent_name: "Jane Doe",
    headshot_url: null,
    event_name: "UFC Test 1",
  },
  {
    id: "fight-2",
    date: "2021-06-15T00:00:00.000Z",
    finish_seconds: 120,
    method: "KO",
    result: "L",
    opponent_id: "opp-2",
    opponent_name: "John Smith",
    headshot_url: null,
    event_name: "UFC Test 2",
  },
];

const BASE_DIMENSIONS = { width: 800, height: 600 };
const IDENTITY_TRANSFORM: Transform = { scale: 1, translateX: 0, translateY: 0 };

describe("useFightScatterState", () => {
  it("computes domains, scales, and quadtree entries", () => {
    const { result } = renderHook(() =>
      useFightScatterState({
        fights: SAMPLE_FIGHTS,
        dimensions: BASE_DIMENSIONS,
        transform: IDENTITY_TRANSFORM,
      })
    );

    const { domain, renderedFights, quadTree } = result.current;

    expect(domain.xMin).toBeLessThan(domain.xMax);
    expect(domain.yMin).toBeLessThan(domain.yMax);
    expect(renderedFights).toHaveLength(SAMPLE_FIGHTS.length);

    const target = renderedFights[0];
    const found = quadTree.find(target.screenX, target.screenY);
    expect(found?.id).toBe(target.id);
  });

  it("respects custom Y domains", () => {
    const domainY: [number, number] = [0, 600];
    const { result } = renderHook(() =>
      useFightScatterState({
        fights: SAMPLE_FIGHTS,
        dimensions: BASE_DIMENSIONS,
        transform: IDENTITY_TRANSFORM,
        domainY,
      })
    );

    expect(result.current.domain.yMin).toBe(domainY[0]);
    expect(result.current.domain.yMax).toBe(domainY[1]);
  });
});

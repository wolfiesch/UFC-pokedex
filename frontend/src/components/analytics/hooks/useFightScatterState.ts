import { useMemo } from "react";
import { scaleLinear, scaleTime, type ScaleLinear, type ScaleTime } from "d3-scale";
import { quadtree, type Quadtree } from "d3-quadtree";

import { computeDomain } from "@/lib/fight-scatter-utils";
import type { ScatterFight, Transform } from "@/types/fight-scatter";

/**
 * Screen-space dimensions of the scatter plot container.
 */
export interface ScatterDimensions {
  width: number;
  height: number;
}

/**
 * Bounding box values describing the computed temporal and duration domain.
 */
export interface ScatterDomain {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
}

/**
 * Fight enriched with the derived screen coordinates for hit testing.
 */
export interface RenderedFight extends ScatterFight {
  screenX: number;
  screenY: number;
}

interface UseFightScatterStateOptions {
  fights: ScatterFight[];
  domainY?: [number, number];
  dimensions: ScatterDimensions;
  transform: Transform;
}

interface UseFightScatterStateResult {
  domain: ScatterDomain;
  xScale: ScaleTime<number, number>;
  yScale: ScaleLinear<number, number>;
  renderedFights: RenderedFight[];
  quadTree: Quadtree<RenderedFight>;
}

/**
 * Derives memoised scales, domains, and hit-testing structures for the scatter plot.
 * All expensive calculations live here to keep the consuming component declarative.
 */
export function useFightScatterState({
  fights,
  domainY,
  dimensions,
  transform,
}: UseFightScatterStateOptions): UseFightScatterStateResult {
  const domain = useMemo<ScatterDomain>(() => {
    const computed = computeDomain(fights);
    return {
      ...computed,
      yMin: domainY ? domainY[0] : computed.yMin,
      yMax: domainY ? domainY[1] : computed.yMax,
    };
  }, [fights, domainY]);

  const xScale = useMemo<ScaleTime<number, number>>(
    () =>
      scaleTime<number, number>()
        .domain([new Date(domain.xMin), new Date(domain.xMax)])
        .range([40, dimensions.width - 40]),
    [domain.xMin, domain.xMax, dimensions.width]
  );

  const yScale = useMemo<ScaleLinear<number, number>>(
    () =>
      scaleLinear()
        .domain([domain.yMax, domain.yMin])
        .range([40, dimensions.height - 40]),
    [domain.yMin, domain.yMax, dimensions.height]
  );

  const renderedFights = useMemo<RenderedFight[]>(() => {
    return fights.map((fight) => {
      const date = new Date(fight.date);
      const baseX = xScale(date) || 0;
      const baseY = yScale(fight.finish_seconds) || 0;

      return {
        ...fight,
        screenX: baseX * transform.scale + transform.translateX,
        screenY: baseY * transform.scale + transform.translateY,
      };
    });
  }, [fights, transform.scale, transform.translateX, transform.translateY, xScale, yScale]);

  const quadTree = useMemo<Quadtree<RenderedFight>>(() => {
    return quadtree<RenderedFight>()
      .x((d) => d.screenX)
      .y((d) => d.screenY)
      .addAll(renderedFights);
  }, [renderedFights]);

  return { domain, xScale, yScale, renderedFights, quadTree };
}

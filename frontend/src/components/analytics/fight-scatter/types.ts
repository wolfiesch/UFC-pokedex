import type { ScatterFight } from "@/types/fight-scatter";

/**
 * Dimensions of the scatter canvas container in CSS pixels.
 */
export interface FightScatterDimensions {
  width: number;
  height: number;
}

/**
 * Extends the base scatter fight with projected screen coordinates for
 * interactive hit-testing and tooltip anchoring.
 */
export interface RenderedFight extends ScatterFight {
  screenX: number;
  screenY: number;
}

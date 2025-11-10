/**
 * Visual configuration constants shared across FightScatter hooks and components.
 * Values were extracted from the legacy monolithic implementation to keep
 * rendering consistent after the refactor.
 */
export const VISUAL_CONFIG = {
  /** Diameter of fighter headshot markers in canvas pixels. */
  MARKER_SIZE: 40,
  /** Stroke width applied to marker borders that encode fight outcomes. */
  BORDER_WIDTH: 2,
  /** Size of the small method badge rendered in the upper-right corner. */
  BADGE_SIZE: 12,
  /** Palette for fight outcomes, trend overlays, and density heatmap. */
  COLORS: {
    WIN: "#2ecc71",
    LOSS: "#e74c3c",
    DRAW: "#95a5a6",
    TREND: "rgba(52, 152, 219, 0.6)",
    HEATMAP_COOL: "rgba(52, 152, 219, 0)",
    HEATMAP_WARM: "rgba(231, 76, 60, 0.4)",
  },
  /** Opacity to apply to non-matching fights when filters are active. */
  FILTER_OPACITY: 0.15,
  /** Min/Max zoom multipliers enforced by the d3 zoom behaviour. */
  ZOOM_EXTENT: [0.5, 5] as [number, number],
  /** Duration for tweened transitions (reserved for future animation work). */
  ANIMATION_DURATION: 200,
  /** Search radius (in px) when determining the closest fight for tooltips. */
  HIT_TEST_RADIUS: 25,
} as const;

/**
 * Readable abbreviations for fight methods shown within marker badges.
 */
export const METHOD_ABBREV: Record<"KO" | "SUB" | "DEC" | "OTHER", string> = {
  KO: "KO",
  SUB: "SUB",
  DEC: "DEC",
  OTHER: "?",
};

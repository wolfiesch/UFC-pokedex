/**
 * Visual configuration constants shared across Fight Scatter components.
 * Centralizing the styling knobs keeps renderers and hooks declarative and
 * prevents magic numbers from leaking throughout the implementation.
 */
export const FIGHT_SCATTER_VISUALS = {
  MARKER_SIZE: 40,
  BORDER_WIDTH: 2,
  BADGE_SIZE: 12,
  FILTER_OPACITY: 0.15,
  ZOOM_EXTENT: [0.5, 5] as [number, number],
  ANIMATION_DURATION: 200,
  HIT_TEST_RADIUS: 25,
  COLORS: {
    WIN: "#2ecc71",
    LOSS: "#e74c3c",
    DRAW: "#95a5a6",
    TREND: "rgba(52, 152, 219, 0.6)",
    HEATMAP_COOL: "rgba(52, 152, 219, 0)",
    HEATMAP_WARM: "rgba(231, 76, 60, 0.4)",
  },
} as const;

/**
 * Badge abbreviations for the supported fight finish methods.
 */
export const METHOD_ABBREVIATIONS = {
  KO: "KO",
  SUB: "SUB",
  DEC: "DEC",
  OTHER: "?",
} as const;

/**
 * Curated colour palette for UFC divisions.
 *
 * Each division receives a perceptually distinct hue anchored in sRGB while
 * providing companion tones for highlights, muted states, and glow effects.
 * The palette also supplies colourblind-friendly alternates derived from
 * higher lightness and reduced saturation to maintain contrast under common
 * vision deficiencies.
 */

export type ColorVisionMode = "standard" | "colorblind";

/**
 * Full tonal ramp for a single division.  `base` is the canonical hex used in
 * charts, `emphasis` is a lighter accent, `muted` is a darker complementary
 * tone, and `glow` is the colour applied to SVG drop-shadows.  The
 * `colorblind` swatch prioritises luminance contrast for deuteranopia and
 * protanopia simulations.
 */
export interface DivisionColorRamp {
  readonly base: string;
  readonly emphasis: string;
  readonly muted: string;
  readonly glow: string;
  readonly colorblind: string;
}

/** Default ramp applied when a division lacks dedicated branding. */
export const DEFAULT_DIVISION_RAMP: DivisionColorRamp = {
  base: "#64748b",
  emphasis: "#94a3b8",
  muted: "#475569",
  glow: "#cbd5f5",
  colorblind: "#7d8599",
};

/**
 * Helper used to clamp floating point values so lightness adjustments never
 * exceed CSS-compatible ranges.
 */
function clamp(value: number, minimum = 0, maximum = 1): number {
  return Math.min(maximum, Math.max(minimum, value));
}

/** Convert a hex triplet into an HSL tuple so that tone ramps can be derived. */
function hexToHsl(hex: string): { h: number; s: number; l: number } {
  const normalized = hex.replace("#", "");
  const r = Number.parseInt(normalized.slice(0, 2), 16) / 255;
  const g = Number.parseInt(normalized.slice(2, 4), 16) / 255;
  const b = Number.parseInt(normalized.slice(4, 6), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;

  let hue = 0;
  if (delta !== 0) {
    switch (max) {
      case r:
        hue = ((g - b) / delta + (g < b ? 6 : 0)) * 60;
        break;
      case g:
        hue = ((b - r) / delta + 2) * 60;
        break;
      default:
        hue = ((r - g) / delta + 4) * 60;
        break;
    }
  }

  const lightness = (max + min) / 2;
  const saturation =
    delta === 0 ? 0 : delta / (1 - Math.abs(2 * lightness - 1));

  return { h: hue, s: saturation, l: lightness };
}

/** Convert HSL values back into a 6-character hex string. */
function hslToHex(h: number, s: number, l: number): string {
  const chroma = (1 - Math.abs(2 * l - 1)) * s;
  const huePrime = h / 60;
  const intermediate = chroma * (1 - Math.abs((huePrime % 2) - 1));

  let r = 0;
  let g = 0;
  let b = 0;

  if (huePrime >= 0 && huePrime < 1) {
    r = chroma;
    g = intermediate;
  } else if (huePrime >= 1 && huePrime < 2) {
    r = intermediate;
    g = chroma;
  } else if (huePrime >= 2 && huePrime < 3) {
    g = chroma;
    b = intermediate;
  } else if (huePrime >= 3 && huePrime < 4) {
    g = intermediate;
    b = chroma;
  } else if (huePrime >= 4 && huePrime < 5) {
    r = intermediate;
    b = chroma;
  } else if (huePrime >= 5 && huePrime < 6) {
    r = chroma;
    b = intermediate;
  }

  const match = l - chroma / 2;
  const toHex = (channel: number) => {
    const value = Math.round((channel + match) * 255)
      .toString(16)
      .padStart(2, "0");
    return value;
  };

  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

/**
 * Produce a tonal ramp from a base colour.  The helper keeps the hue constant
 * and only tweaks saturation/lightness so that the palette remains cohesive.
 */
function buildRamp(base: string, colorblindOverride?: string): DivisionColorRamp {
  const { h, s, l } = hexToHsl(base);
  const emphasis = hslToHex(h, clamp(s * 0.9 + 0.08), clamp(l + 0.12));
  const muted = hslToHex(h, clamp(s * 0.75), clamp(l * 0.7));
  const glow = hslToHex(h, clamp(s * 0.85), clamp(l + 0.2));
  const colorblind = colorblindOverride ?? hslToHex(h, clamp(s * 0.55), clamp(0.62));
  return { base, emphasis, muted, glow, colorblind };
}

/**
 * Explicitly curated ramps for the most common UFC divisions.  Keys must match
 * the API payload exactly to ensure lookups remain deterministic.
 */
export const CURATED_DIVISION_COLORS: Record<string, DivisionColorRamp> = {
  Flyweight: buildRamp("#0091ea", "#2f9de3"),
  Bantamweight: buildRamp("#f97316", "#f88d3d"),
  Featherweight: buildRamp("#16a34a", "#30a95c"),
  Lightweight: buildRamp("#7c3aed", "#8867f1"),
  Welterweight: buildRamp("#ef4444", "#f1625d"),
  Middleweight: buildRamp("#0ea5e9", "#3caee6"),
  "Light Heavyweight": buildRamp("#f59e0b", "#f6ad38"),
  Heavyweight: buildRamp("#4c1d95", "#7050c1"),
  "Women's Strawweight": buildRamp("#ec4899", "#f06fb1"),
  "Women's Flyweight": buildRamp("#38bdf8", "#64c6f7"),
  "Women's Bantamweight": buildRamp("#fb7185", "#fc8b9b"),
  "Women's Featherweight": buildRamp("#a855f7", "#b27df8"),
  FeatherweightWEC: buildRamp("#1abc9c", "#42c7ad"),
  Catchweight: buildRamp("#f472b6", "#f694c7"),
};

/**
 * Supplemental hues for unexpected or historic divisions.  The values favour
 * high contrast and are evenly spaced around the colour wheel.
 */
const FALLBACK_BASES: readonly string[] = [
  "#0284c7",
  "#c026d3",
  "#059669",
  "#facc15",
  "#fb7185",
  "#6366f1",
  "#14b8a6",
  "#f97316",
];

const fallbackRampCache = new Map<string, DivisionColorRamp>();

/**
 * Retrieve the curated ramp for a division or generate a deterministic
 * fallback when unknown.  Unknown divisions reuse the same fallback ramp on
 * subsequent requests so that colours remain stable across re-renders.
 */
export function getDivisionColorRamp(
  division: string | null | undefined,
): DivisionColorRamp {
  const normalized = division?.trim();
  if (!normalized) {
    return DEFAULT_DIVISION_RAMP;
  }

  const curated = CURATED_DIVISION_COLORS[normalized];
  if (curated) {
    return curated;
  }

  const cached = fallbackRampCache.get(normalized);
  if (cached) {
    return cached;
  }

  const hash = normalized
    .split("")
    .reduce((accumulator, character) => accumulator + character.charCodeAt(0), 0);
  const base = FALLBACK_BASES[Math.abs(hash) % FALLBACK_BASES.length];
  const ramp = buildRamp(base);
  fallbackRampCache.set(normalized, ramp);
  return ramp;
}

/**
 * Convenience accessor returning the correct swatch for the requested vision
 * mode.  The default branch uses the core brand hue, while the colourblind
 * path supplies a softer tone with higher luminance contrast.
 */
export function resolveDivisionColor(
  division: string | null | undefined,
  mode: ColorVisionMode = "standard",
): string {
  const ramp = getDivisionColorRamp(division);
  return mode === "colorblind" ? ramp.colorblind : ramp.base;
}

/** Quick helper returning the glow colour for a division. */
export function resolveDivisionGlow(division: string | null | undefined): string {
  return getDivisionColorRamp(division).glow;
}

/** Lighter emphasis tone used for UI swatches and hover affordances. */
export function resolveDivisionEmphasis(
  division: string | null | undefined,
): string {
  return getDivisionColorRamp(division).emphasis;
}


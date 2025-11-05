/**
 * Type definitions for Fight Scatter Visualization Component
 */

/**
 * Fight method categories
 */
export type FightMethod = "KO" | "SUB" | "DEC" | "OTHER";

/**
 * Fight result categories
 */
export type FightResult = "W" | "L" | "D";

/**
 * Individual fight data point for scatter visualization
 */
export interface ScatterFight {
  /** Unique fight identifier */
  id: string;
  /** ISO date string of the fight */
  date: string;
  /** Total fight duration in seconds (for finishes) or maximum time (for decisions) */
  finish_seconds: number;
  /** Method of victory/loss */
  method: FightMethod;
  /** Fight result from fighter's perspective */
  result: FightResult;
  /** Opponent's fighter ID */
  opponent_id: string | null;
  /** Opponent's name for display */
  opponent_name: string;
  /** URL to opponent's headshot image */
  headshot_url: string | null;
  /** Event name */
  event_name: string;
  /** Round number (if available) */
  round?: number | null;
  /** Time within round (MM:SS format) */
  time?: string | null;
  /** Link to fight card on UFCStats */
  fight_card_url?: string | null;
}

/**
 * Hexagonal bin for density heatmap visualization
 */
export interface HexbinBucket {
  /** Grid column index */
  i: number;
  /** Grid row index */
  j: number;
  /** Number of fights in this bucket */
  count: number;
}

/**
 * Data point for trend line
 */
export interface TrendPoint {
  /** X-axis value (timestamp in milliseconds) */
  x: number;
  /** Y-axis value (finish seconds) */
  y: number;
}

/**
 * Props for FightScatter component
 */
export interface FightScatterProps {
  /** Array of fights to visualize */
  fights: ScatterFight[];
  /** Pre-computed hexbin buckets for density visualization (optional) */
  hexbins?: HexbinBucket[];
  /** Y-axis domain override [min, max] in seconds (optional) */
  domainY?: [number, number];
  /** Toggle density heatmap overlay */
  showDensity?: boolean;
  /** Toggle trend line overlay */
  showTrend?: boolean;
  /** Filter by results (empty array = show all) */
  filterResults?: FightResult[];
  /** Filter by methods (empty array = show all) */
  filterMethods?: FightMethod[];
  /** Callback when a fight is selected */
  onSelectFight?: (fightId: string) => void;
  /** Custom CSS class */
  className?: string;
  /** Chart height in pixels (default: 600) */
  height?: number;
}

/**
 * Transform state for zoom/pan
 */
export interface Transform {
  /** Scale factor (zoom level) */
  scale: number;
  /** X-axis translation in pixels */
  translateX: number;
  /** Y-axis translation in pixels */
  translateY: number;
}

/**
 * Tooltip state
 */
export interface TooltipState {
  /** X position in pixels */
  x: number;
  /** Y position in pixels */
  y: number;
  /** Fight data to display */
  fight: ScatterFight;
}

/**
 * Worker message for trend computation
 */
export interface TrendWorkerRequest {
  /** Type of message */
  type: "compute";
  /** Data points to smooth */
  points: TrendPoint[];
  /** Window size for rolling median (default: 5) */
  windowSize?: number;
}

/**
 * Worker response with computed trend
 */
export interface TrendWorkerResponse {
  /** Type of message */
  type: "result" | "error";
  /** Smoothed trend points */
  points?: TrendPoint[];
  /** Error message if computation failed */
  error?: string;
}

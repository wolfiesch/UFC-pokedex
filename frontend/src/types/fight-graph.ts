/**
 * Shared TypeScript interfaces describing the fight graph payload
 * returned by the backend `/fightweb/graph` endpoint.
 *
 * These definitions mirror the `FightGraphResponse` pydantic schema
 * so downstream visualization components can rely on strong typing
 * without needing to inspect the API payload at runtime.
 */
export interface FightGraphNode {
  /** Unique identifier mapping to the fighter record in the database. */
  fighter_id: string;
  /** Human readable fighter name, used for labels and tooltips. */
  name: string;
  /** Optional division categorisation (e.g. "Lightweight"). */
  division?: string | null;
  /** Professional record as a pre-formatted string ("12-2-0"). */
  record?: string | null;
  /** Publicly accessible image for avatars and preview cards. */
  image_url?: string | null;
  /** Total number of fights available for the selected time range. */
  total_fights: number;
  /** Date of the most recent event included in the aggregation. */
  latest_event_date?: string | null;
}

export interface FightGraphLink {
  /** Fighter ID representing the source of the connection. */
  source: string;
  /** Fighter ID representing the target of the connection. */
  target: string;
  /** Number of fights contested between the fighters. */
  fights: number;
  /** Optional metadata describing when the rivalry began. */
  first_event_name?: string | null;
  first_event_date?: string | null;
  /** Optional metadata describing the latest recorded fight. */
  last_event_name?: string | null;
  last_event_date?: string | null;
  /** Outcome breakdown keyed by fighter ID with win/draw/loss tallies. */
  result_breakdown: Record<string, Record<string, number>>;
}

export interface FightGraphRivalryInsight {
  source: string;
  target: string;
  fights: number;
  source_name?: string | null;
  target_name?: string | null;
  last_event_name?: string | null;
  last_event_date?: string | null;
}

export interface FightGraphTopFighterInsight {
  fighter_id: string;
  name: string;
  division?: string | null;
  total_fights: number;
  degree: number;
}

export interface FightGraphDivisionBreakdownEntry {
  division: string;
  count: number;
  percentage: number;
}

export interface FightGraphInsights {
  average_fights_per_fighter?: number;
  network_density?: number;
  division_breakdown?: FightGraphDivisionBreakdownEntry[];
  top_fighters?: FightGraphTopFighterInsight[];
  busiest_rivalries?: FightGraphRivalryInsight[];
}

export interface FightGraphMetadata {
  /** ISO timestamp indicating when the aggregation was generated. */
  generated_at?: string;
  /** Collection of analytics computed by the backend. */
  insights?: FightGraphInsights;
  /** Additional contextual data keyed by strings. */
  [key: string]: unknown;
}

export interface FightGraphResponse {
  /** Nodes representing fighters participating in the network. */
  nodes: FightGraphNode[];
  /** Undirected edges linking fighters who have competed. */
  links: FightGraphLink[];
  /** Metadata supplementing the graph payload. */
  metadata: FightGraphMetadata;
}

export interface FightGraphQueryParams {
  division?: string;
  startYear?: number;
  endYear?: number;
  limit?: number;
  includeUpcoming?: boolean;
}

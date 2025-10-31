export type FighterListItem = {
  fighter_id: string;
  detail_url: string;
  name: string;
  nickname?: string | null;
  division?: string | null;
  height?: string | null;
  weight?: string | null;
  reach?: string | null;
  stance?: string | null;
  dob?: string | null;
};

export type FightHistoryEntry = {
  fight_id: string;
  event_name: string;
  event_date?: string | null;
  opponent: string;
  opponent_id?: string | null;
  result: string;
  method: string;
  round?: number | null;
  time?: string | null;
  fight_card_url?: string | null;
  stats?: Record<string, string | number | null | undefined>;
};

export type FighterDetail = FighterListItem & {
  record?: string | null;
  leg_reach?: string | null;
  age?: number | null;
  striking: Record<string, string | number | null | undefined>;
  grappling: Record<string, string | number | null | undefined>;
  significant_strikes: Record<string, string | number | null | undefined>;
  takedown_stats: Record<string, string | number | null | undefined>;
  fight_history: FightHistoryEntry[];
};

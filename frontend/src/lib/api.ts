import type { FighterListItem } from "./types";

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export interface PaginatedFightersResponse {
  fighters: FighterListItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export async function getFighters(
  limit = 20,
  offset = 0
): Promise<PaginatedFightersResponse> {
  const apiUrl = getApiBaseUrl();
  const response = await fetch(
    `${apiUrl}/fighters/?limit=${limit}&offset=${offset}`,
    { cache: "no-store" }
  );
  if (!response.ok) {
    throw new Error("Failed to fetch fighters");
  }
  return response.json();
}

export async function getRandomFighter(): Promise<FighterListItem> {
  const apiUrl = getApiBaseUrl();
  const response = await fetch(`${apiUrl}/fighters/random`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Failed to fetch random fighter");
  }
  return response.json();
}

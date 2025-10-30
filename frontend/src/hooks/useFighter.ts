"use client";

import { useEffect, useState } from "react";

import type { FighterDetail } from "@/lib/types";
import { getApiBaseUrl } from "@/lib/api";

export function useFighter(fighterId: string) {
  const [fighter, setFighter] = useState<FighterDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!fighterId) return;
    let active = true;
    async function load() {
      setIsLoading(true);
      try {
        const response = await fetch(`${getApiBaseUrl()}/fighters/${fighterId}`, {
          cache: "no-store",
        });
        if (response.status === 404) {
          if (active) {
            setFighter(null);
          }
          return;
        }
        if (!response.ok) {
          throw new Error(`Failed to load fighter (${response.status})`);
        }
        const data: FighterDetail = await response.json();
        if (active) {
          setFighter(data);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Unknown error");
          setFighter(null);
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [fighterId]);

  return { fighter, isLoading, error };
}

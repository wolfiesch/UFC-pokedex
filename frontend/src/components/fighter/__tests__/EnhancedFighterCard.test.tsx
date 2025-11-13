import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { EnhancedFighterCard } from "../../fighter/EnhancedFighterCard";
import type { FighterListItem } from "@/lib/types";

describe("EnhancedFighterCard – list-provided streaks", () => {
  const base: FighterListItem = {
    fighter_id: "test-id",
    detail_url: "/fighters/test-id",
    name: "Test Fighter",
    record: "10-2-0",
    division: "Lightweight",
    image_url: null,
    is_current_champion: false,
    is_former_champion: false,
    was_interim: false,
  };

  it("renders streak badge from list fields without hover", () => {
    render(
      <EnhancedFighterCard
        fighter={{
          ...base,
          current_streak_type: "win",
          current_streak_count: 3,
        }}
      />,
    );

    // Badge uses the numeric label only (e.g., "3")
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("does not render badge when count < 2", () => {
    render(
      <EnhancedFighterCard
        fighter={{
          ...base,
          current_streak_type: "win",
          current_streak_count: 1,
        }}
      />,
    );

    expect(screen.queryByText("1")).toBeNull();
  });
});

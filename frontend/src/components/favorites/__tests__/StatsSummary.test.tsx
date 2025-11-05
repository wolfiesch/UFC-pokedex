import { render, screen } from "@testing-library/react";

import StatsSummary from "../StatsSummary";
import type { FavoriteCollectionStats } from "@/lib/types";

describe("StatsSummary", () => {
  const stats: FavoriteCollectionStats = {
    total_fighters: 3,
    win_rate: 0.6667,
    result_breakdown: {
      win: 2,
      loss: 1,
      upcoming: 1,
    },
    divisions: ["Lightweight", "Welterweight"],
    upcoming_fights: [
      {
        fighter_id: "fighter-a",
        opponent_name: "Opponent Z",
        event_name: "UFC 301",
        event_date: "2024-06-01",
        weight_class: "Lightweight",
      },
    ],
  };

  it("displays headline metrics and breakdown values", () => {
    render(<StatsSummary collectionName="Watchlist" stats={stats} />);

    expect(screen.getByText(/Watchlist snapshot/i)).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText(/66.7%/i)).toBeInTheDocument();
    expect(screen.getByText(/win rate/i)).toBeInTheDocument();
    expect(screen.getByText(/UFC 301/i)).toBeInTheDocument();
  });
});

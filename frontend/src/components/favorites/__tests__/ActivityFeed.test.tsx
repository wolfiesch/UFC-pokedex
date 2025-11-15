import { render, screen } from "@testing-library/react";

import ActivityFeed from "../ActivityFeed";
import type { FavoriteActivityItem } from "@/lib/types";

describe("ActivityFeed", () => {
  const activity: FavoriteActivityItem[] = [
    {
      entry_id: 1,
      fighter_id: "fighter-a",
      fighter_name: "Fighter Alpha",
      action: "added",
      occurred_at: "2024-01-01T00:00:00Z",
      metadata: { notes: "Scouted at UFC 300" },
    },
  ];

  it("shows timeline entries when activity exists", () => {
    render(<ActivityFeed activity={activity} />);
    expect(screen.getByText(/fighter alpha/i)).toBeInTheDocument();
    expect(screen.getByText(/Scouted at UFC 300/i)).toBeInTheDocument();
  });

  it("renders a placeholder when no activity is present", () => {
    render(<ActivityFeed activity={[]} />);
    expect(screen.getByText(/No recorded actions yet/i)).toBeInTheDocument();
  });
});

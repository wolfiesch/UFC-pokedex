import { render, screen } from "@testing-library/react";

import CollectionsGrid from "../CollectionsGrid";
import type { FavoriteEntry } from "@/lib/types";

describe("CollectionsGrid", () => {
  const sampleEntries: FavoriteEntry[] = [
    {
      id: 1,
      fighter_id: "fighter-a",
      position: 0,
      notes: "Primary striker",
      tags: ["striking", "prospect"],
      metadata: {},
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    },
    {
      id: 2,
      fighter_id: "fighter-b",
      position: 1,
      notes: null,
      tags: [],
      metadata: {},
      created_at: "2024-01-02T00:00:00Z",
      updated_at: "2024-01-02T00:00:00Z",
    },
  ];

  it("renders a helpful placeholder when no entries exist", () => {
    render(<CollectionsGrid entries={[]} onReorder={vi.fn()} />);
    expect(
      screen.getByText(/No fighters in this collection yet/i)
    ).toBeInTheDocument();
  });

  it("renders each fighter with notes and tag chips", () => {
    render(<CollectionsGrid entries={sampleEntries} onReorder={vi.fn()} />);

    expect(screen.getByText(/fighter-a/i)).toBeInTheDocument();
    expect(screen.getByText(/Primary striker/i)).toBeInTheDocument();
    expect(screen.getByText(/striking/i)).toBeInTheDocument();
    expect(screen.getByText(/Position #1/i)).toBeInTheDocument();
  });
});

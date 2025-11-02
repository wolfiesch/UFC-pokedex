import { render, screen } from "@testing-library/react";
import LeaderboardTable from "../LeaderboardTable";
import type { LeaderboardEntry } from "@/lib/types";

describe("LeaderboardTable", () => {
  const sampleEntries: LeaderboardEntry[] = [
    {
      fighter_id: "1",
      fighter_name: "Fighter One",
      metric_value: 15,
      detail_url: "/fighters/1",
    },
    {
      fighter_id: "2",
      fighter_name: "Fighter Two",
      metric_value: 12.5,
    },
  ];

  it("renders leaderboard rows with rank and formatted values", () => {
    render(
      <LeaderboardTable
        title="Top Finishers"
        description="Measured by total finishes."
        entries={sampleEntries}
        metricLabel="Finishes"
      />
    );

    expect(screen.getByText("Top Finishers")).toBeInTheDocument();
    expect(screen.getByText("Measured by total finishes.")).toBeInTheDocument();
    expect(screen.getByText("Finishes")).toBeInTheDocument();
    expect(screen.getByText("Fighter One")).toBeInTheDocument();
    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getByText("12.5")).toBeInTheDocument();
  });

  it("renders loading placeholder when isLoading is true", () => {
    render(
      <LeaderboardTable title="Loading" entries={[]} isLoading metricLabel="Score" />
    );

    expect(screen.getByRole("status")).toHaveTextContent("Loading leaderboard");
  });

  it("renders error message when error prop is set", () => {
    render(
      <LeaderboardTable title="Error" entries={[]} error="Something went wrong" />
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong");
  });

  it("renders empty state when no entries provided", () => {
    render(<LeaderboardTable title="Empty" entries={[]} />);

    expect(screen.getByText(/No leaderboard data available/i)).toBeInTheDocument();
  });
});

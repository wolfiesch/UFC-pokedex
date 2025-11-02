import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";

import {
  LeaderboardCard,
  StatsHubSection,
  TrendPanel,
  type LeaderboardEntry,
  type TrendSeries,
} from "../index";

const leaderboardEntries: LeaderboardEntry[] = [
  {
    fighterId: "alpha-1",
    fighterName: "Alpha One",
    metricLabel: "Striking accuracy",
    metricValue: 0.64,
    delta: 0.08,
  },
  {
    fighterId: "bravo-2",
    fighterName: "Bravo Two",
    metricLabel: "Striking accuracy",
    metricValue: 0.58,
    delta: 0.05,
  },
  {
    fighterId: "charlie-3",
    fighterName: "Charlie Three",
    metricLabel: "Striking accuracy",
    metricValue: 0.55,
  },
];

const trendSeries: TrendSeries[] = [
  {
    fighterId: "alpha-1",
    fighterName: "Alpha One",
    metricLabel: "Sig. strikes landed / min",
    points: [
      { label: "Jan", value: 3.1 },
      { label: "Feb", value: 3.4 },
      { label: "Mar", value: 3.7 },
    ],
  },
  {
    fighterId: "bravo-2",
    fighterName: "Bravo Two",
    metricLabel: "Takedown success",
    points: [
      { label: "Jan", value: 0.45 },
      { label: "Feb", value: 0.5 },
      { label: "Mar", value: 0.52 },
    ],
  },
];

afterEach(() => {
  cleanup();
});

describe("Stats Hub presentational components", () => {
  it("renders a leaderboard with highlighted rows", () => {
    render(<LeaderboardCard title="Top Accuracy" entries={leaderboardEntries} highlightCount={2} />);

    expect(screen.getByText("Top Accuracy")).toBeInTheDocument();
    expect(screen.getByText("Alpha One")).toBeInTheDocument();
    expect(screen.getByText("64.0%")).toBeInTheDocument();
    expect(screen.getByText(/▲ 8.0%/)).toBeInTheDocument();
  });

  it("prints trend deltas and sparkline table", () => {
    render(<TrendPanel title="Momentum" series={trendSeries} />);

    expect(screen.getByText("Momentum")).toBeInTheDocument();
    expect(screen.getAllByText("Alpha One")).toHaveLength(1);
    expect(
      screen.getByText((content, element) => element?.textContent?.trim() === "+0.30")
    ).toBeInTheDocument();
    expect(screen.getAllByText("Mar")).toHaveLength(2);
  });

  it("composes leaderboard and trend widgets for Stats Hub", () => {
    render(
      <StatsHubSection
        leaderboardTitle="Accuracy Leaders"
        leaderboardEntries={leaderboardEntries}
        trendTitle="Recent Momentum"
        trendSeries={trendSeries}
      />
    );

    expect(screen.getByText("Accuracy Leaders")).toBeInTheDocument();
    expect(screen.getByText("Recent Momentum")).toBeInTheDocument();
    expect(screen.getAllByText(/Striking accuracy/)).toHaveLength(
      leaderboardEntries.length
    );
  });
});

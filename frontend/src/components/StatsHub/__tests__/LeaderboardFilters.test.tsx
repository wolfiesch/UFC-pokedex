import { render, screen } from "@testing-library/react";

import LeaderboardFilters from "../LeaderboardFilters";

describe("LeaderboardFilters", () => {
  const noop = () => {};

  it("shows default helper text about the 5 fight minimum", () => {
    render(
      <LeaderboardFilters
        division={null}
        minFights={5}
        onDivisionChange={noop}
        onMinFightsChange={noop}
      />,
    );

    expect(
      screen.getByText(/only fighters with ≥5 ufc fights are shown by default/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/results may be noisy/i),
    ).not.toBeInTheDocument();
  });

  it("shows a warning when the slider drops below 5 fights", () => {
    render(
      <LeaderboardFilters
        division={null}
        minFights={3}
        onDivisionChange={noop}
        onMinFightsChange={noop}
      />,
    );

    expect(screen.getByText(/results may be noisy/i)).toBeInTheDocument();
  });
});

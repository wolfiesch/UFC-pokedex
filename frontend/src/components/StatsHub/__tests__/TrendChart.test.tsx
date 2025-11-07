import { render, screen } from "@testing-library/react";
import type { TrendSeries } from "@/lib/types";

vi.mock("next/dynamic", () => ({
  __esModule: true,
  default:
    () =>
    // eslint-disable-next-line react/display-name
      (props: { series: TrendSeries[] }) => (
        <div data-testid="trend-chart-stub">{props.series.length} series</div>
      ),
}));

import TrendChart from "../TrendChart";

describe("TrendChart", () => {
  const sampleSeries: TrendSeries[] = [
    {
      metric_id: "finishes_over_time",
      label: "Finishes Over Time",
      points: [
        { timestamp: "2024-01-01", value: 3 },
        { timestamp: "2024-02-01", value: 4 },
      ],
    },
  ];

  it("renders loading state when isLoading is true", () => {
    render(<TrendChart title="Trends" series={sampleSeries} isLoading />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading trend data");
  });

  it("renders error message when provided", () => {
    render(<TrendChart title="Trends" series={sampleSeries} error="Unable to load" />);

    expect(screen.getByRole("alert")).toHaveTextContent("Unable to load");
  });

  it("renders empty state when no series available", () => {
    render(<TrendChart title="Trends" series={[]} />);

    expect(screen.getByText(/No trend information/i)).toBeInTheDocument();
  });

  it("renders chart stub when series provided", () => {
    render(<TrendChart title="Trends" series={sampleSeries} />);

    expect(screen.getByTestId("trend-chart-stub")).toHaveTextContent("1 series");
  });

  it("matches snapshot with populated trend data", () => {
    const { container } = render(
      <TrendChart
        title="Trends"
        description="Win streak duration over time"
        series={sampleSeries}
      />
    );

    expect(container.firstChild).toMatchSnapshot();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import FighterGrid from "../FighterGrid";
import type { FighterListItem } from "@/lib/types";

vi.mock("../fighter/EnhancedFighterCard", () => ({
  EnhancedFighterCard: ({ fighter }: { fighter: FighterListItem }) => (
    <div data-testid="fighter-card">{fighter.name}</div>
  ),
}));

function createFighter(id: number): FighterListItem {
  return {
    fighter_id: `fighter-${id}`,
    detail_url: `/fighters/${id}`,
    name: `Fighter ${id}`,
    nickname: null,
    division: null,
    height: null,
    weight: null,
    reach: null,
    stance: null,
    dob: null,
    image_url: null,
    resolved_image_url: null,
  };
}

describe("FighterGrid pagination controls", () => {
  it("renders pagination summary and page indicator", () => {
    render(
      <FighterGrid
        fighters={[createFighter(1), createFighter(2)]}
        isLoading={false}
        isFetchingPage={false}
        error={null}
        total={8}
        limit={2}
        offset={2}
        canNextPage
        canPreviousPage
      />,
    );

    expect(screen.getByText(/Showing 3-4 of 8 fighters/)).toBeInTheDocument();
    expect(screen.getByText(/Page 2 of 4/)).toBeInTheDocument();
  });

  it("invokes next and previous callbacks when buttons are clicked", () => {
    const handleNext = vi.fn();
    const handlePrev = vi.fn();

    render(
      <FighterGrid
        fighters={[createFighter(1), createFighter(2)]}
        isLoading={false}
        isFetchingPage={false}
        error={null}
        total={6}
        limit={2}
        offset={2}
        canNextPage
        canPreviousPage
        onNextPage={handleNext}
        onPreviousPage={handlePrev}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fireEvent.click(screen.getByRole("button", { name: /prev/i }));

    expect(handleNext).toHaveBeenCalledTimes(1);
    expect(handlePrev).toHaveBeenCalledTimes(1);
  });

  it("disables controls while fetching or when at pagination bounds", () => {
    const { rerender } = render(
      <FighterGrid
        fighters={[createFighter(1), createFighter(2)]}
        isLoading={false}
        isFetchingPage
        error={null}
        total={10}
        limit={2}
        offset={4}
        canNextPage
        canPreviousPage
      />,
    );

    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /prev/i })).toBeDisabled();

    rerender(
      <FighterGrid
        fighters={[createFighter(1), createFighter(2)]}
        isLoading={false}
        isFetchingPage={false}
        error={null}
        total={2}
        limit={2}
        offset={0}
        canNextPage={false}
        canPreviousPage={false}
      />,
    );

    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /prev/i })).toBeDisabled();
  });
});

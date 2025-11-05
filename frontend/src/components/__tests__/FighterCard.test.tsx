import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import FighterCard from "../FighterCard";
import type { FighterListItem } from "@/lib/types";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

const baseFighter: FighterListItem = {
  fighter_id: "fighter-1",
  detail_url: "/fighters/1",
  name: "Amanda Nunes",
  nickname: null,
  division: "Bantamweight",
  height: null,
  weight: null,
  reach: null,
  stance: null,
  dob: null,
  image_url: null,
  resolved_image_url: null,
};

describe("FighterCard image rendering", () => {
  it("prefers the resolved image URL from the API when available", () => {
    const fighter: FighterListItem = {
      ...baseFighter,
      resolved_image_url: "https://cdn.example.com/portraits/amanda.jpg",
      image_url: "https://legacy.example.com/portrait.jpg",
    };

    render(<FighterCard fighter={fighter} />);

    const image = screen.getByRole("img", { name: fighter.name });
    expect(image).toHaveAttribute("src", fighter.resolved_image_url);
  });

  it("falls back to the legacy image URL when the resolved URL is missing", () => {
    const fighter: FighterListItem = {
      ...baseFighter,
      image_url: "https://legacy.example.com/portrait.jpg",
      resolved_image_url: null,
    };

    render(<FighterCard fighter={fighter} />);

    const image = screen.getByRole("img", { name: fighter.name });
    expect(image).toHaveAttribute("src", fighter.image_url);
  });

  it("shows the placeholder if the image fails to load", async () => {
    const fighter: FighterListItem = {
      ...baseFighter,
      resolved_image_url: "https://cdn.example.com/broken.jpg",
    };

    render(<FighterCard fighter={fighter} />);

    const image = screen.getByRole("img", { name: fighter.name });
    fireEvent.error(image);

    await waitFor(() => {
      expect(screen.getByText("AN")).toBeInTheDocument();
    });
  });
});

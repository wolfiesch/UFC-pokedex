/**
 * Unit tests for fight scatter utilities
 */

import { describe, it, expect } from "vitest";
import {
  calculateFinishSeconds,
  convertFightToScatterPoint,
  computeDomain,
  filterFights,
} from "../fight-scatter-utils";
import type { FightHistoryEntry } from "../types";
import { resolveImageUrl } from "../utils";

describe("calculateFinishSeconds", () => {
  it("should calculate finish time for first round finish", () => {
    const seconds = calculateFinishSeconds(1, "2:34", false, 3);
    expect(seconds).toBe(2 * 60 + 34); // 154 seconds
  });

  it("should calculate finish time for second round finish", () => {
    const seconds = calculateFinishSeconds(2, "1:15", false, 3);
    expect(seconds).toBe(300 + 1 * 60 + 15); // 375 seconds
  });

  it("should calculate finish time for third round finish", () => {
    const seconds = calculateFinishSeconds(3, "4:59", false, 5);
    expect(seconds).toBe(600 + 4 * 60 + 59); // 899 seconds
  });

  it("should return full fight time for decisions (3 rounds)", () => {
    const seconds = calculateFinishSeconds(null, null, true, 3);
    expect(seconds).toBe(900); // 3 * 300
  });

  it("should return full fight time for decisions (5 rounds)", () => {
    const seconds = calculateFinishSeconds(null, null, true, 5);
    expect(seconds).toBe(1500); // 5 * 300
  });

  it("should handle invalid time format", () => {
    const seconds = calculateFinishSeconds(2, "invalid", false, 3);
    expect(seconds).toBe(600); // End of round 2
  });

  it("should handle missing round", () => {
    const seconds = calculateFinishSeconds(null, "1:00", true, 3);
    expect(seconds).toBe(900); // Full fight
  });
});

describe("convertFightToScatterPoint", () => {
  it("should convert a KO finish correctly", () => {
    const fight: FightHistoryEntry = {
      fight_id: "fight1",
      event_name: "UFC 300",
      event_date: "2024-01-15",
      opponent: "John Doe",
      opponent_id: "opponent1",
      result: "W",
      method: "KO/TKO",
      round: 2,
      time: "3:45",
      fight_card_url: "https://ufcstats.com/fight1",
      stats: {},
    };

    const scatter = convertFightToScatterPoint(fight);

    expect(scatter.id).toBe("fight1");
    expect(scatter.method).toBe("KO");
    expect(scatter.result).toBe("W");
    expect(scatter.finish_seconds).toBe(300 + 3 * 60 + 45); // 525
    expect(scatter.opponent_name).toBe("John Doe");
    expect(scatter.headshot_url).toBe(
      resolveImageUrl("/images/fighters/opponent1.jpg")
    );
  });

  it("should convert a submission finish correctly", () => {
    const fight: FightHistoryEntry = {
      fight_id: "fight2",
      event_name: "UFC 301",
      event_date: "2024-02-01",
      opponent: "Jane Smith",
      opponent_id: "opponent2",
      result: "L",
      method: "Submission",
      round: 1,
      time: "4:30",
      fight_card_url: null,
      stats: {},
    };

    const scatter = convertFightToScatterPoint(fight);

    expect(scatter.method).toBe("SUB");
    expect(scatter.result).toBe("L");
    expect(scatter.finish_seconds).toBe(4 * 60 + 30); // 270
  });

  it("should convert a decision correctly", () => {
    const fight: FightHistoryEntry = {
      fight_id: "fight3",
      event_name: "UFC 302",
      event_date: "2024-03-01",
      opponent: "Bob Johnson",
      opponent_id: null,
      result: "W",
      method: "Decision - Unanimous",
      round: 3,
      time: "5:00",
      fight_card_url: null,
      stats: {},
    };

    const scatter = convertFightToScatterPoint(fight);

    expect(scatter.method).toBe("DEC");
    expect(scatter.finish_seconds).toBe(900); // Full 3 rounds
    expect(scatter.headshot_url).toBe("/img/placeholder-fighter.png"); // No opponent_id
  });

  it("should normalize unknown methods to OTHER", () => {
    const fight: FightHistoryEntry = {
      fight_id: "fight4",
      event_name: "UFC 303",
      event_date: "2024-04-01",
      opponent: "Test Fighter",
      opponent_id: "opponent4",
      result: "L",
      method: "DQ",
      round: 1,
      time: "0:30",
      fight_card_url: null,
      stats: {},
    };

    const scatter = convertFightToScatterPoint(fight);

    expect(scatter.method).toBe("OTHER");
  });
});

describe("computeDomain", () => {
  it("should compute correct domain for multiple fights", () => {
    const fights = [
      {
        id: "1",
        date: "2024-01-01",
        finish_seconds: 100,
        method: "KO" as const,
        result: "W" as const,
        opponent_id: "opp1",
        opponent_name: "Fighter 1",
        headshot_url: null,
        event_name: "Event 1",
      },
      {
        id: "2",
        date: "2024-06-01",
        finish_seconds: 800,
        method: "DEC" as const,
        result: "L" as const,
        opponent_id: "opp2",
        opponent_name: "Fighter 2",
        headshot_url: null,
        event_name: "Event 2",
      },
    ];

    const domain = computeDomain(fights);

    expect(domain.yMin).toBeLessThan(100);
    expect(domain.yMax).toBeGreaterThan(800);
    expect(domain.xMin).toBeLessThan(new Date("2024-01-01").getTime());
    expect(domain.xMax).toBeGreaterThan(new Date("2024-06-01").getTime());
  });

  it("should return default domain for empty fights array", () => {
    const domain = computeDomain([]);

    expect(domain.yMin).toBe(0);
    expect(domain.yMax).toBe(1500);
    expect(domain.xMax - domain.xMin).toBeGreaterThan(0);
  });
});

describe("filterFights", () => {
  const fights = [
    {
      id: "1",
      date: "2024-01-01",
      finish_seconds: 100,
      method: "KO" as const,
      result: "W" as const,
      opponent_id: "opp1",
      opponent_name: "Fighter 1",
      headshot_url: null,
      event_name: "Event 1",
    },
    {
      id: "2",
      date: "2024-02-01",
      finish_seconds: 500,
      method: "SUB" as const,
      result: "W" as const,
      opponent_id: "opp2",
      opponent_name: "Fighter 2",
      headshot_url: null,
      event_name: "Event 2",
    },
    {
      id: "3",
      date: "2024-03-01",
      finish_seconds: 900,
      method: "DEC" as const,
      result: "L" as const,
      opponent_id: "opp3",
      opponent_name: "Fighter 3",
      headshot_url: null,
      event_name: "Event 3",
    },
  ];

  it("should filter by result", () => {
    const { filtered } = filterFights(fights, ["W"], []);

    expect(filtered.length).toBe(2);
    expect(filtered[0].id).toBe("1");
    expect(filtered[1].id).toBe("2");
  });

  it("should filter by method", () => {
    const { filtered } = filterFights(fights, [], ["KO"]);

    expect(filtered.length).toBe(1);
    expect(filtered[0].id).toBe("1");
  });

  it("should filter by both result and method", () => {
    const { filtered } = filterFights(fights, ["W"], ["SUB"]);

    expect(filtered.length).toBe(1);
    expect(filtered[0].id).toBe("2");
  });

  it("should return all fights when no filters", () => {
    const { filtered } = filterFights(fights, [], []);

    expect(filtered.length).toBe(3);
  });

  it("should return match indices", () => {
    const { matchIndices } = filterFights(fights, ["W"], []);

    expect(matchIndices.has(0)).toBe(true);
    expect(matchIndices.has(1)).toBe(true);
    expect(matchIndices.has(2)).toBe(false);
  });
});

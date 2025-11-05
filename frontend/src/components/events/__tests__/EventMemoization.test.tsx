import { describe, expect, it } from "vitest";

import {
  EnhancedFightCard,
  enhancedFightCardPropsEqual,
} from "@/components/events/EnhancedFightCard";
import {
  EventStatsPanel,
  eventStatsPanelPropsEqual,
} from "@/components/events/EventStatsPanel";
import {
  FightCardSection,
  fightCardSectionPropsEqual,
} from "@/components/events/FightCardSection";
import {
  RelatedEventsWidget,
  relatedEventsWidgetPropsEqual,
} from "@/components/events/RelatedEventsWidget";

const sampleFight = {
  fight_id: "1",
  fighter_1_id: "f1",
  fighter_1_name: "Fighter One",
  fighter_2_id: "f2",
  fighter_2_name: "Fighter Two",
  weight_class: "Lightweight",
  result: "Win",
  method: "KO",
  round: 1,
  time: "1:23",
};

describe("event component memoization guards", () => {
  it("wraps key components in React.memo", () => {
    const memoSymbol = Symbol.for("react.memo");

    expect(EventStatsPanel.$$typeof).toBe(memoSymbol);
    expect(FightCardSection.$$typeof).toBe(memoSymbol);
    expect(RelatedEventsWidget.$$typeof).toBe(memoSymbol);
    expect(EnhancedFightCard.$$typeof).toBe(memoSymbol);
  });

  it("treats identical event stats props as equal", () => {
    const prevProps = { fights: [sampleFight], eventName: "UFC 200" };
    const nextProps = { fights: [sampleFight], eventName: "UFC 200" };

    expect(eventStatsPanelPropsEqual(prevProps, nextProps)).toBe(true);

    const changedProps = {
      fights: [
        {
          ...sampleFight,
          fight_id: "2",
        },
      ],
      eventName: "UFC 200",
    };

    expect(eventStatsPanelPropsEqual(prevProps, changedProps)).toBe(false);
  });

  it("collapses redundant fight card renders when fight IDs match", () => {
    const section = {
      section: "main" as const,
      label: "Main Card",
      fights: [sampleFight],
    };

    const prevProps = { section, eventName: "UFC 200", allFights: [sampleFight] };
    const nextProps = { section, eventName: "UFC 200", allFights: [sampleFight] };

    expect(fightCardSectionPropsEqual(prevProps, nextProps)).toBe(true);

    const modified = {
      section: {
        ...section,
        fights: [{ ...sampleFight, fight_id: "changed" }],
      },
      eventName: "UFC 200",
      allFights: [sampleFight],
    };

    expect(fightCardSectionPropsEqual(prevProps, modified)).toBe(false);
  });

  it("ignores related events with identical identifiers", () => {
    const related = [
      {
        event_id: "abc",
        name: "UFC Sample",
        date: "2024-01-01",
        location: "Las Vegas",
        status: "completed",
        event_type: "ppv" as const,
      },
    ];

    const prevProps = {
      currentEventId: "abc",
      relatedEvents: related,
      reason: "location" as const,
    };
    const nextProps = {
      currentEventId: "abc",
      relatedEvents: related,
      reason: "location" as const,
    };

    expect(relatedEventsWidgetPropsEqual(prevProps, nextProps)).toBe(true);

    const changedRelated = {
      ...nextProps,
      relatedEvents: [{ ...related[0], event_id: "different" }],
    };

    expect(relatedEventsWidgetPropsEqual(prevProps, changedRelated)).toBe(false);
  });

  it("keeps enhanced fighter cards stable when props are identical", () => {
    const prevProps = {
      fight: sampleFight,
      isTitleFight: true,
      isMainEvent: false,
      fighterRecord: "10-1-0",
    };
    const nextProps = { ...prevProps };

    expect(enhancedFightCardPropsEqual(prevProps, nextProps)).toBe(true);

    const changed = { ...nextProps, fighterRecord: "11-1-0" };
    expect(enhancedFightCardPropsEqual(prevProps, changed)).toBe(false);
  });
});

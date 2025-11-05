"use client";

import { memo, useMemo } from "react";

import {
  Fight,
  FightCardSection as FightCardSectionType,
  isTitleFight,
  isMainEvent,
} from "@/lib/fight-utils";

import EnhancedFightCard from "./EnhancedFightCard";

interface FightCardSectionProps {
  section: FightCardSectionType;
  eventName: string;
  allFights: Fight[];
}

/**
 * Component for displaying a section of fight card (Main Card, Prelims, Early Prelims)
 */
function FightCardSectionComponent({
  section,
  eventName,
  allFights,
}: FightCardSectionProps) {
  const sectionConfig = useMemo(
    () => ({
      main: {
        icon: "🔥",
        bgClass: "bg-gradient-to-r from-red-900/30 to-orange-900/30",
        borderClass: "border-red-700",
      },
      prelims: {
        icon: "⚡",
        bgClass: "bg-gradient-to-r from-blue-900/30 to-indigo-900/30",
        borderClass: "border-blue-700",
      },
      early_prelims: {
        icon: "✨",
        bgClass: "bg-gradient-to-r from-purple-900/30 to-pink-900/30",
        borderClass: "border-purple-700",
      },
    }),
    []
  );

  const config = sectionConfig[section.section];

  const fights = useMemo(() => section.fights, [section.fights]);

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div
        className={`
          sticky top-0 z-10 rounded-lg border p-4
          ${config.bgClass} ${config.borderClass}
          backdrop-blur-sm
        `}
      >
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-bold text-white">
            {config.icon} {section.label}
          </h3>
          <span className="rounded-full bg-gray-700/50 px-3 py-1 text-sm font-medium text-gray-300">
            {section.fights.length} {section.fights.length === 1 ? "Fight" : "Fights"}
          </span>
        </div>
      </div>

      {/* Fights */}
      <div className="space-y-3">
        {fights.map((fight) => {
          const isTitleBout = isTitleFight(fight, eventName);
          const isMain = isMainEvent(fight, allFights, eventName);

          return (
            <EnhancedFightCard
              key={fight.fight_id}
              fight={fight}
              isTitleFight={isTitleBout}
              isMainEvent={isMain}
            />
          );
        })}
      </div>
    </div>
  );
}

const areSectionPropsEqual = (
  previous: Readonly<FightCardSectionProps>,
  next: Readonly<FightCardSectionProps>
): boolean => {
  if (
    previous.eventName !== next.eventName ||
    previous.section.section !== next.section.section ||
    previous.section.label !== next.section.label
  ) {
    return false;
  }

  if (previous.section.fights.length !== next.section.fights.length) {
    return false;
  }

  return previous.section.fights.every(
    (fight, index) => fight.fight_id === next.section.fights[index]?.fight_id
  );
};

export const FightCardSection = memo(
  FightCardSectionComponent,
  areSectionPropsEqual
);

/** Exported for unit tests that validate memo guard behaviour. */
export const fightCardSectionPropsEqual = areSectionPropsEqual;

export default FightCardSection;

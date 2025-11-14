"use client";

import { format } from "date-fns";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { FighterOddsHistoryEntry } from "@/types/odds";
import { QualityBadge } from "./QualityBadge";

type OddsHistoryTableProps = {
  history: FighterOddsHistoryEntry[];
};

export function OddsHistoryTable({ history }: OddsHistoryTableProps) {
  if (!history.length) {
    return (
      <p className="text-sm text-muted-foreground">
        We haven&apos;t indexed odds data for this fighter yet. Re-run the
        scraper or try another athlete.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Event</TableHead>
            <TableHead>Opponent</TableHead>
            <TableHead>Opening</TableHead>
            <TableHead>Closing</TableHead>
            <TableHead>Points</TableHead>
            <TableHead>Quality</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {history.map((fight) => (
            <TableRow key={fight.id}>
              <TableCell className="font-medium">
                <div className="flex flex-col">
                  <span>{fight.event_name}</span>
                  <span className="text-xs text-muted-foreground">
                    {fight.event_date
                      ? format(new Date(fight.event_date), "MMM d, yyyy")
                      : "TBA"}
                  </span>
                </div>
              </TableCell>
              <TableCell className="text-sm">{fight.opponent_name}</TableCell>
              <TableCell className="text-sm">
                {fight.opening_odds ?? "—"}
              </TableCell>
              <TableCell className="text-sm">
                {fight.closing_range?.end ??
                  fight.closing_range?.start ??
                  "—"}
              </TableCell>
              <TableCell className="text-sm font-semibold">
                {fight.num_odds_points}
              </TableCell>
              <TableCell>
                <QualityBadge tier={fight.data_quality} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

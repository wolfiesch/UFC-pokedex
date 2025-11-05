import type { FavoriteActivityItem } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export type ActivityFeedProps = {
  /** Items representing the chronological history of collection changes. */
  activity: FavoriteActivityItem[];
};

/**
 * Render a lightweight timeline describing how the collection evolved over time.
 */
export function ActivityFeed({ activity }: ActivityFeedProps) {
  return (
    <section aria-labelledby="favorites-activity-heading" className="space-y-4">
      <header>
        <h2 id="favorites-activity-heading" className="text-xl font-bold tracking-tight">
          Activity feed
        </h2>
        <p className="text-sm text-muted-foreground">
          Recent additions, edits, and reorder operations captured for auditing.
        </p>
      </header>

      <Card className="border-border/60 bg-card/80">
        <CardHeader>
          <CardTitle className="text-sm font-semibold text-muted-foreground">
            Timeline
          </CardTitle>
        </CardHeader>
        <CardContent>
          {activity.length ? (
            <ol className="space-y-3">
              {activity.map((item) => (
                <li
                  key={`${item.entry_id}-${item.occurred_at}-${item.action}`}
                  className="flex flex-col gap-1 rounded-lg border border-border/40 bg-background/40 p-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-foreground">
                      {item.action} – {item.fighter_id}
                    </span>
                    <span className="text-xs text-muted-foreground/80">{item.occurred_at}</span>
                  </div>
                  {Object.keys(item.metadata ?? {}).length ? (
                    <pre className="whitespace-pre-wrap text-xs text-muted-foreground">
                      {JSON.stringify(item.metadata, null, 2)}
                    </pre>
                  ) : null}
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-muted-foreground">No recorded actions yet.</p>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

export default ActivityFeed;

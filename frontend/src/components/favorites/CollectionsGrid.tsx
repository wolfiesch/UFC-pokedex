"use client";

import { useEffect, useMemo, useState } from "react";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  type DragEndEvent,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import type { FavoriteEntry } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type CollectionsGridProps = {
  /** Ordered fighters currently stored in the selected collection. */
  entries: FavoriteEntry[];
  /** Callback invoked when drag-and-drop completes with the new ordering. */
  onReorder: (entryIds: number[]) => Promise<void> | void;
  /** Optional flag to disable interactions while a mutation is pending. */
  isReordering?: boolean;
};

/**
 * Sortable list item rendered inside the drag-and-drop context.
 */
function SortableEntry({ entry }: { entry: FavoriteEntry }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: entry.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
  } as const;

  return (
    <Card
      ref={setNodeRef}
      style={style}
      className="border-border/70 bg-card/90 shadow-sm transition focus-within:ring-2 focus-within:ring-primary"
    >
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <CardTitle className="text-base font-semibold tracking-tight">
          {entry.fighter_id}
        </CardTitle>
        <Button
          variant="outline"
          size="sm"
          className="cursor-grab touch-none select-none"
          {...attributes}
          {...listeners}
        >
          Drag
        </Button>
      </CardHeader>
      <CardContent className="flex flex-col gap-2 text-sm text-muted-foreground">
        {entry.notes ? <p className="leading-relaxed">{entry.notes}</p> : null}
        <div className="flex flex-wrap items-center gap-2">
          {entry.tags.map((tag) => (
            <span
              key={`${entry.id}-${tag}`}
              className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
            >
              {tag}
            </span>
          ))}
          {!entry.tags.length ? (
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs">No tags yet</span>
          ) : null}
        </div>
        <p className="text-xs uppercase tracking-wide text-muted-foreground/80">
          Position #{entry.position + 1}
        </p>
      </CardContent>
    </Card>
  );
}

/**
 * Grid component that renders favorite fighters and wires up drag-and-drop
 * interactions so users can curate their preferred ordering.
 */
export function CollectionsGrid({ entries, onReorder, isReordering = false }: CollectionsGridProps) {
  const [orderedEntries, setOrderedEntries] = useState<FavoriteEntry[]>(entries);

  // Track the previous ordering to allow quick rollback if the API call fails.
  const [previousEntries, setPreviousEntries] = useState<FavoriteEntry[]>(entries);

  useEffect(() => {
    setOrderedEntries(entries);
    setPreviousEntries(entries);
  }, [entries]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const entryIds = useMemo(() => orderedEntries.map((entry) => entry.id), [orderedEntries]);

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) {
      return;
    }

    const oldIndex = orderedEntries.findIndex((entry) => entry.id === active.id);
    const newIndex = orderedEntries.findIndex((entry) => entry.id === over.id);
    if (oldIndex === -1 || newIndex === -1) {
      return;
    }

    const nextOrder = arrayMove(orderedEntries, oldIndex, newIndex);
    setPreviousEntries(orderedEntries);
    setOrderedEntries(nextOrder);

    try {
      await onReorder(nextOrder.map((entry) => entry.id));
    } catch (error) {
      console.error("Failed to persist favorites reorder", error);
      setOrderedEntries(previousEntries);
    }
  }

  if (!orderedEntries.length) {
    return (
      <div className="rounded-3xl border border-dashed border-border/60 bg-card/40 p-10 text-center text-sm text-muted-foreground">
        No fighters in this collection yet. Use the search tools to add your first favorite.
      </div>
    );
  }

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <SortableContext items={entryIds} strategy={verticalListSortingStrategy}>
        <div
          className={cn("grid gap-4 md:grid-cols-2", isReordering && "pointer-events-none opacity-70")}
          aria-busy={isReordering}
        >
          {orderedEntries.map((entry) => (
            <SortableEntry key={entry.id} entry={{ ...entry, position: entry.position }} />
          ))}
        </div>
      </SortableContext>
      {isReordering ? (
        <p className="mt-4 text-sm text-muted-foreground" aria-live="polite">
          Saving new ordering…
        </p>
      ) : null}
    </DndContext>
  );
}

export default CollectionsGrid;

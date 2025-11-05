"use client";

import { useCallback, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import client from "@/lib/api-client";
import type { EventDetail, EventListItem } from "@/lib/types";

interface UseEventDetailsOptions {
  /** When true the hook fetches related events that share the same location. */
  includeRelated?: boolean;
  /** Maximum number of related events to request from the backend. */
  relatedLimit?: number;
  /** Enable React Suspense semantics for consumers that opt in. */
  suspense?: boolean;
}

interface UseEventDetailsResult {
  event: EventDetail | null;
  relatedEvents: EventListItem[];
  isLoading: boolean;
  isFetching: boolean;
  error: Error | null;
  refetch: () => void;
}

const EVENT_DETAILS_QUERY_KEY = "event-details" as const;
const RELATED_EVENTS_QUERY_KEY = "event-related" as const;

const eventQueryConfig = {
  staleTime: 1000 * 60 * 5,
  gcTime: 1000 * 60 * 30,
};

async function fetchEventDetail(eventId: string): Promise<EventDetail> {
  const { data, error } = await client.GET("/events/{event_id}", {
    params: {
      path: {
        event_id: eventId,
      },
    },
  });

  if (!data || error) {
    throw new Error(`Failed to fetch event ${eventId}`);
  }

  return data as EventDetail;
}

async function fetchRelatedEvents(
  location: string,
  limit: number
): Promise<EventListItem[]> {
  const { data, error } = await client.GET("/events/search/", {
    params: {
      query: {
        location,
        limit,
      },
    },
  });

  if (!data || error) {
    throw new Error(`Failed to fetch related events for ${location}`);
  }

  return (data.events ?? []) as EventListItem[];
}

export function useEventDetails(
  eventId: string,
  options: UseEventDetailsOptions = {}
): UseEventDetailsResult {
  const {
    includeRelated = true,
    relatedLimit = 6,
    suspense = false,
  } = options;

  const queryClient = useQueryClient();

  const normalizedId = useMemo(() => eventId.trim(), [eventId]);
  const isEnabled = normalizedId.length > 0;

  const eventQueryKey = useMemo(
    () => [EVENT_DETAILS_QUERY_KEY, normalizedId] as const,
    [normalizedId]
  );

  const {
    data: eventData,
    error: eventError,
    isLoading,
    isFetching,
  } = useQuery<EventDetail, Error>({
    queryKey: eventQueryKey,
    queryFn: () => fetchEventDetail(normalizedId),
    enabled: isEnabled,
    suspense,
    ...eventQueryConfig,
  });

  const eventLocation = eventData?.location ?? null;

  const normalizedLocation = useMemo(
    () => eventLocation?.trim().toLowerCase() ?? null,
    [eventLocation]
  );

  const relatedQueryKey = useMemo(
    () =>
      [
        RELATED_EVENTS_QUERY_KEY,
        normalizedLocation ?? "",
        relatedLimit,
      ] as const,
    [normalizedLocation, relatedLimit]
  );

  const shouldFetchRelated = includeRelated && Boolean(normalizedLocation);

  const {
    data: relatedData,
    error: relatedError,
    isFetching: isFetchingRelated,
  } = useQuery<EventListItem[], Error>({
    queryKey: relatedQueryKey,
    queryFn: () => fetchRelatedEvents(normalizedLocation ?? "", relatedLimit),
    enabled: shouldFetchRelated,
    suspense,
    staleTime: 1000 * 60 * 10,
    gcTime: 1000 * 60 * 30,
  });

  const error = eventError ?? relatedError ?? null;

  const event = useMemo(() => eventData ?? null, [eventData]);
  const relatedEvents = useMemo(
    () => relatedData ?? [],
    [relatedData]
  );

  const refetch = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: eventQueryKey });
    if (shouldFetchRelated) {
      void queryClient.invalidateQueries({ queryKey: relatedQueryKey });
    }
  }, [queryClient, eventQueryKey, relatedQueryKey, shouldFetchRelated]);

  return {
    event,
    relatedEvents,
    isLoading,
    isFetching: isFetching || isFetchingRelated,
    error,
    refetch,
  };
}

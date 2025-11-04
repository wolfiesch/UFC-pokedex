"use client";

import { ReactNode, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

/**
 * QueryProvider wraps the application with a TanStack Query client instance so every
 * component can leverage declarative data fetching, caching, and background updates.
 * The provider memoizes a single client per browser session which prevents duplicate
 * network requests when navigating between pages or re-rendering client components.
 */
export function QueryProvider({ children }: { children: ReactNode }) {
  /**
   * Lazily create the QueryClient so that it only executes on the client, and so
   * the same instance is reused for the lifetime of the provider. The default
   * configuration keeps fighter lists warm for five minutes which drastically
   * reduces redundant calls when returning to the roster screen.
   */
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            /**
             * Cache successful queries for five minutes. When a user navigates away
             * and back to a page, TanStack Query can serve the cached data instantly
             * without re-requesting from the API.
             */
            staleTime: 1000 * 60 * 5,
            /**
             * Retain cached fighter data for thirty minutes before garbage collection
             * so we can benefit from cache hits during longer browsing sessions.
             */
            gcTime: 1000 * 60 * 30,
            /**
             * Automatically retry transient errors twice which matches our existing
             * fetchWithRetry behaviour and improves resilience to flaky networks.
             */
            retry: 2,
            /** Provide more granular loading states during background refetches. */
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

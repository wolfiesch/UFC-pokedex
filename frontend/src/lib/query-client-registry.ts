import { QueryClient } from "@tanstack/react-query";

let activeQueryClient: QueryClient | null = null;

/**
 * Store a reference to the client-side QueryClient instance so utility
 * functions outside of React hooks (e.g. preloading helpers) can access the
 * shared cache without creating duplicate clients.
 */
export function registerQueryClient(client: QueryClient): void {
  activeQueryClient = client;
}

/**
 * Retrieve the globally-registered QueryClient instance, if one exists.
 */
export function getRegisteredQueryClient(): QueryClient | null {
  return activeQueryClient;
}

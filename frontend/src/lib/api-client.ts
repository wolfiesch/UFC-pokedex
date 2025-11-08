/**
 * Type-safe API client using openapi-fetch
 *
 * This client is auto-generated from the OpenAPI schema and provides:
 * - Full TypeScript type safety for all API endpoints
 * - Autocomplete for request/response types
 * - Compile-time validation of API calls
 *
 * To regenerate types: `make types-generate`
 */

import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./generated/api-schema";
import { ApiError } from "./errors";
import { logger } from "./logger";
import { resolveApiBaseUrl } from "./resolve-api-base-url";

const DEFAULT_TIMEOUT_MS = 30000; // 30 seconds
const MAX_RETRY_ATTEMPTS = 3;
const RETRY_DELAY_MS = 1000; // 1 second base delay

/**
 * Get the API base URL from environment variables
 */
function getApiBaseUrl(): string {
  return resolveApiBaseUrl(
    process.env.NEXT_PUBLIC_API_BASE_URL,
    "http://localhost:8000"
  );
}

/**
 * Sleep for a specified duration (for retry delays)
 */
async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Calculate exponential backoff delay
 */
function getRetryDelay(retryCount: number, baseDelay = RETRY_DELAY_MS): number {
  return baseDelay * Math.pow(2, retryCount - 1);
}

/**
 * Custom middleware for logging requests/responses
 */
const loggingMiddleware: Middleware = {
  async onRequest({ request }) {
    const method = request.method;
    const url = request.url;
    logger.logRequest(method, url);
    return request;
  },

  async onResponse({ response, request }) {
    const method = request.method;
    const url = request.url;
    logger.logResponse(method, url, response.status, 0); // Duration tracked separately
    return response;
  },
};

/**
 * Custom middleware for error handling and transformation
 */
const errorHandlingMiddleware: Middleware = {
  async onResponse({ response }) {
    if (!response.ok && response.status >= 400) {
      const requestId = response.headers.get("X-Request-ID") || undefined;

      try {
        const errorData = await response.clone().json();
        throw ApiError.fromResponse(errorData, response.status);
      } catch (error) {
        if (error instanceof ApiError) {
          throw error;
        }
        // If we can't parse the error response, create a generic error
        throw new ApiError(
          response.statusText || "Request failed",
          {
            statusCode: response.status,
            detail: `HTTP ${response.status} error occurred`,
            requestId,
          }
        );
      }
    }
    return response;
  },
};

/**
 * Custom fetch wrapper with retry logic
 */
async function fetchWithRetry(
  input: RequestInfo | URL,
  init?: RequestInit,
  maxRetries = MAX_RETRY_ATTEMPTS
): Promise<Response> {
  let lastError: Error | null = null;
  const method = init?.method || "GET";
  const url = input.toString();

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const startTime = Date.now();

      if (attempt > 0) {
        const delay = getRetryDelay(attempt);
        logger.logRetry(method, url, attempt, maxRetries);
        await sleep(delay);
      }

      // Add timeout handling
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

      try {
        const response = await fetch(input, {
          ...init,
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        return response;
      } catch (error) {
        clearTimeout(timeoutId);
        if (error instanceof Error && error.name === "AbortError") {
          throw ApiError.fromTimeout(DEFAULT_TIMEOUT_MS);
        }
        throw error;
      }
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (error instanceof ApiError) {
        // Don't retry if error is not retryable
        if (!error.isRetryable || attempt === maxRetries) {
          logger.logApiError(method, url, error);
          throw error;
        }
      } else {
        // Network error or other fetch error
        const networkError = ApiError.fromNetworkError(lastError, attempt);
        if (attempt === maxRetries) {
          logger.logApiError(method, url, networkError);
          throw networkError;
        }
        lastError = networkError;
      }
    }
  }

  // This should never be reached, but TypeScript needs it
  throw lastError || new ApiError("Request failed after retries");
}

/**
 * Create the type-safe API client
 *
 * This client provides full type safety for all API endpoints defined in the OpenAPI schema.
 * All request parameters and response types are automatically inferred from the schema.
 */
export const client = createClient<paths>({
  baseUrl: getApiBaseUrl(),
  fetch: fetchWithRetry as typeof fetch,
  headers: {
    "Content-Type": "application/json",
  },
  // Disable caching for real-time data
  cache: "no-store",
});

// Add middleware for logging and error handling
client.use(loggingMiddleware);
client.use(errorHandlingMiddleware);

/**
 * Export the client as default for convenience
 *
 * Usage:
 * ```ts
 * import client from '@/lib/api-client';
 *
 * // GET request with full type safety
 * const { data, error } = await client.GET('/fighters/', {
 *   params: {
 *     query: { limit: 20, offset: 0 }
 *   }
 * });
 *
 * // POST request
 * const { data, error } = await client.POST('/fighters/compare', {
 *   body: { fighter_ids: ['id1', 'id2'] }
 * });
 * ```
 */
export default client;

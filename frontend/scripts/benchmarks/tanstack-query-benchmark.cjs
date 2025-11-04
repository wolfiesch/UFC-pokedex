#!/usr/bin/env node

/**
 * Simple Node.js benchmark that compares the time spent performing multiple
 * fighter roster fetches sequentially using the legacy imperative approach
 * versus the new TanStack Query caching layer. The simulation introduces an
 * artificial latency so the benefit of caching becomes apparent without needing
 * to spin up the entire application stack.
 */

const { performance } = require("node:perf_hooks");
const { setTimeout: delay } = require("node:timers/promises");
const { QueryClient } = require("@tanstack/react-query");

/**
 * Simulate the UFC backend returning a paginated roster payload. Each invocation
 * increments a counter so we can see how many network calls were required for a
 * benchmark run.
 */
async function simulateRosterFetch(state) {
  state.calls += 1;
  await delay(state.latencyMs);
  return {
    fighters: Array.from({ length: 20 }, (_, index) => ({
      fighter_id: `benchmark-${index}`,
      detail_url: `/fighters/benchmark-${index}`,
      name: `Benchmark Fighter ${index + 1}`,
    })),
    total: 100,
    limit: 20,
    offset: 0,
    has_more: false,
  };
}

async function runLegacyBenchmark(iterations, latencyMs) {
  const state = { calls: 0, latencyMs };
  const start = performance.now();
  for (let attempt = 0; attempt < iterations; attempt += 1) {
    // eslint-disable-next-line no-await-in-loop -- sequential timing is intentional for the benchmark
    await simulateRosterFetch(state);
  }
  const durationMs = performance.now() - start;
  return { durationMs, calls: state.calls };
}

async function runQueryBenchmark(iterations, latencyMs) {
  const state = { calls: 0, latencyMs };
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5,
        gcTime: 1000 * 60 * 30,
      },
    },
  });

  const start = performance.now();
  for (let attempt = 0; attempt < iterations; attempt += 1) {
    // eslint-disable-next-line no-await-in-loop -- sequential timing is intentional for the benchmark
    await client.ensureQueryData({
      queryKey: ["fighters", "benchmark"],
      queryFn: () => simulateRosterFetch(state),
    });
  }
  const durationMs = performance.now() - start;
  client.clear();
  return { durationMs, calls: state.calls };
}

async function main() {
  const iterations = 5;
  const latencyMs = 75;
  const legacy = await runLegacyBenchmark(iterations, latencyMs);
  const cached = await runQueryBenchmark(iterations, latencyMs);

  console.log("Legacy fetch strategy: %s ms across %d calls", legacy.durationMs.toFixed(2), legacy.calls);
  console.log("TanStack Query strategy: %s ms across %d calls", cached.durationMs.toFixed(2), cached.calls);
}

main().catch((error) => {
  console.error("Benchmark failed", error);
  process.exit(1);
});

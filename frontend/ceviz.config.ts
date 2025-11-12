export default {
  // Ignore false positive patterns
  ignore: [
    // Build-time operations (not runtime performance)
    '**/next.config.*',
    '**/*.config.*',

    // Test files
    '**/__tests__/**',
    '**/*.test.*',
    '**/*.spec.*',

    // Benchmark/dev utilities
    '**/scripts/benchmarks/**',
  ],

  // Adjust severity thresholds
  rules: {
    // Only flag nested loops in files processing large datasets
    'nested-loops': {
      severity: 'warning',
      ignore: [
        // Sliding window algorithms (optimal by design)
        '**/trendWorker.ts',
        '**/workers/**',
      ],
    },

    // Only flag array operations on known large datasets
    'array-in-loop': {
      severity: 'warning',
      // Most of our arrays are <100 items (favorites, fight history)
      threshold: 1000,
    },
  },

  // Performance budget
  budget: {
    // More realistic target
    score: 70,

    // Hard limits
    criticalIssues: 5,
    memoryLeaks: 0,
  },
};

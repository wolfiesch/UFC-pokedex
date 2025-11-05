#!/bin/bash

# Performance Benchmark Script
# Run this before and after Phase 1 optimizations to measure improvements

echo "=== UFC Pokedex Performance Benchmark ==="
echo "Date: $(date)"
echo ""

API_BASE="${API_BASE:-http://localhost:8000}"

echo "API Base URL: $API_BASE"
echo ""

# Function to benchmark an endpoint
benchmark_endpoint() {
    local name="$1"
    local url="$2"

    echo "Testing: $name"
    echo "URL: $url"
    curl -w "\n  Time: %{time_total}s\n  Status: %{http_code}\n" -o /dev/null -s "$url"
    echo ""
}

echo "--- Endpoint Benchmarks ---"
echo ""

# Fighter List (tests division index)
benchmark_endpoint "Fighter List (first 20)" "$API_BASE/fighters/?limit=20&offset=0"

# Search with Division Filter (tests division index)
benchmark_endpoint "Search by Division (Welterweight)" "$API_BASE/search/?q=&division=Welterweight"

# Search with Stance Filter (tests stance index)
benchmark_endpoint "Search by Stance (Orthodox)" "$API_BASE/search/?q=&stance=Orthodox"

# Search with Streak Filter (tests streak computation)
benchmark_endpoint "Search with Win Streak" "$API_BASE/search/?q=&streak_type=win&min_streak_count=3"

# Fighter Detail (tests event_date index for fight history)
# Note: Replace this ID with a valid fighter ID from your database
SAMPLE_FIGHTER_ID="${SAMPLE_FIGHTER_ID:-d1053e55f00e53fe}"
benchmark_endpoint "Fighter Detail (with fight history)" "$API_BASE/fighters/$SAMPLE_FIGHTER_ID"

echo "=== Benchmark Complete ==="
echo ""
echo "Expected improvements after Phase 1:"
echo "  - Fighter List: < 100ms (baseline: ~500ms with filters)"
echo "  - Search by Division: < 100ms (baseline: ~500ms)"
echo "  - Search by Stance: < 100ms (baseline: ~500ms)"
echo "  - Fighter Detail: < 50ms (baseline: ~200ms)"
echo ""
echo "To run load tests:"
echo "  ab -n 1000 -c 10 '$API_BASE/fighters/?limit=20&offset=0'"

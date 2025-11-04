#!/usr/bin/env python3
"""Performance testing script to measure API improvements."""

import asyncio
import time
from typing import Any
import httpx
import statistics

BASE_URL = "http://localhost:8000"


async def measure_endpoint(
    client: httpx.AsyncClient, endpoint: str, description: str, runs: int = 10
) -> dict[str, Any]:
    """Measure endpoint performance over multiple runs."""
    times: list[float] = []

    url = f"{BASE_URL}{endpoint}"

    # Warmup run
    await client.get(url)

    # Actual measurements
    for _ in range(runs):
        start = time.perf_counter()
        response = await client.get(url)
        end = time.perf_counter()

        if response.status_code == 200:
            times.append((end - start) * 1000)  # Convert to ms

    if not times:
        return {"error": "All requests failed"}

    return {
        "endpoint": endpoint,
        "description": description,
        "runs": len(times),
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
        "mean_ms": round(statistics.mean(times), 2),
        "median_ms": round(statistics.median(times), 2),
        "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 2) if len(times) > 1 else round(times[0], 2),
    }


async def main():
    """Run performance tests."""
    print("🚀 UFC Pokedex Performance Testing")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test health endpoint
        try:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                print("❌ API is not responding")
                return
            print("✅ API is running\n")
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            return

        # Get a sample fighter ID
        fighters_response = await client.get(f"{BASE_URL}/fighters/?limit=1")
        if fighters_response.status_code != 200:
            print("❌ Cannot fetch fighters")
            return

        fighters_data = fighters_response.json()
        if not fighters_data.get("fighters"):
            print("❌ No fighters in database")
            return

        fighter_id = fighters_data["fighters"][0]["fighter_id"]
        print(f"Using fighter ID: {fighter_id}\n")

        # Define test cases
        tests = [
            (f"/fighters/?limit=20&offset=0", "Fighter list (20 items)"),
            (f"/fighters/{fighter_id}", "Fighter detail page"),
            (f"/search/?q=silva&limit=10", "Search query"),
        ]

        # Run tests
        results = []
        for endpoint, description in tests:
            print(f"Testing: {description}...")
            result = await measure_endpoint(client, endpoint, description, runs=10)
            results.append(result)
            if "error" not in result:
                print(f"  Mean: {result['mean_ms']}ms | Median: {result['median_ms']}ms | P95: {result['p95_ms']}ms")
            else:
                print(f"  ❌ {result['error']}")
            print()

        # Summary
        print("\n" + "=" * 60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)
        print(f"{'Endpoint':<35} {'Mean':<10} {'Median':<10} {'P95':<10}")
        print("-" * 60)
        for result in results:
            if "error" not in result:
                desc = result["description"][:33]
                print(
                    f"{desc:<35} "
                    f"{result['mean_ms']:<10.1f} "
                    f"{result['median_ms']:<10.1f} "
                    f"{result['p95_ms']:<10.1f}"
                )


if __name__ == "__main__":
    asyncio.run(main())

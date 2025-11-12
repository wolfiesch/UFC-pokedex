#!/usr/bin/env python3
"""
Estimate time to scrape historical line movement for all events.

Line movement scraping is MUCH slower than closing odds because:
1. Must click each odds cell (50-150 clicks per event)
2. Wait for Highcharts modal to load (2s per click)
3. Extract chart data
4. Close modal (500ms per click)

Typical event:
- 10-12 fights
- 5-10 bookmakers per fight
- 2 fighters per fight
- Total: 10 fights × 8 bookmakers × 2 fighters = 160 clicks
- Time: 160 clicks × 3s/click = 480 seconds (8 minutes per event)
"""

import json
from pathlib import Path


def estimate_line_movement_time():
    """Estimate total scraping time for line movement."""

    # Load events
    events_file = Path("data/raw/bfo_numbered_events.jsonl")
    if not events_file.exists():
        print("❌ Events file not found")
        return

    with events_file.open() as f:
        events = [json.loads(line) for line in f if line.strip()]

    total_events = len(events)

    # Estimates based on typical UFC events
    print("\n" + "="*70)
    print("⏱️  LINE MOVEMENT SCRAPING TIME ESTIMATES")
    print("="*70)
    print(f"\n📊 Total UFC events: {total_events}")
    print("\nPer-event breakdown:")
    print("  - Average fights per event: 10-12")
    print("  - Average bookmakers per fight: 5-10")
    print("  - Fighters per fight: 2")
    print("  - Clicks per event: 100-240 (avg: 160)")
    print("\nPer-click timing:")
    print("  - Click + chart load: 2.0s")
    print("  - Highcharts extraction: 0.3s")
    print("  - Close modal: 0.5s")
    print("  - Total per click: ~3s")

    # Calculate scenarios
    scenarios = [
        {
            "name": "Conservative (160 clicks/event)",
            "clicks_per_event": 160,
            "seconds_per_click": 3.0,
            "download_delay": 4.0,
        },
        {
            "name": "Optimistic (100 clicks/event)",
            "clicks_per_event": 100,
            "seconds_per_click": 2.5,
            "download_delay": 3.0,
        },
        {
            "name": "Pessimistic (240 clicks/event)",
            "clicks_per_event": 240,
            "seconds_per_click": 3.5,
            "download_delay": 4.0,
        },
    ]

    print("\n" + "="*70)
    print("SCENARIOS")
    print("="*70)

    for scenario in scenarios:
        clicks = scenario["clicks_per_event"]
        per_click = scenario["seconds_per_click"]
        delay = scenario["download_delay"]

        # Time per event
        click_time = clicks * per_click
        page_load_time = delay + 8  # download delay + initial wait
        total_per_event = click_time + page_load_time

        # Total time for all events
        total_seconds = total_events * total_per_event
        total_hours = total_seconds / 3600
        total_days = total_hours / 24

        print(f"\n{scenario['name']}:")
        print(f"  ⏱️  Per event: {total_per_event:.0f}s ({total_per_event/60:.1f} min)")
        print(f"  📊 {total_events} events: {total_hours:.1f} hours ({total_days:.1f} days)")
        print(f"  Settings: {clicks} clicks/event × {per_click}s + {delay}s delay")

    # Recommended approach
    print("\n" + "="*70)
    print("💡 RECOMMENDATIONS")
    print("="*70)
    print("""
1. **Test with 1 event first** (~5 minutes)
   - Measure actual clicks per event
   - Verify Highcharts extraction works
   - Adjust time estimates

2. **Consider filtering by event importance:**
   - Recent events (2020-2025): ~150 events = ~20 hours
   - Numbered UFC only (UFC 200, 300, etc.): ~320 events = ~43 hours
   - All events: ~537 events = ~72 hours

3. **Run in batches with resume capability:**
   - Batch size: 10-20 events
   - Run overnight/weekend
   - Monitor progress and failures

4. **Alternative: Sample historical data:**
   - Scrape line movement for major events only
   - Use closing odds for others
   - Reduces time to ~10-20 hours
""")

    print("="*70 + "\n")


if __name__ == "__main__":
    estimate_line_movement_time()

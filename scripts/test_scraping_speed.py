#!/usr/bin/env python3
"""
Test scraping speed with different delay settings.

Tests a small sample of events (5-10) to measure actual time per event
and determine optimal delay settings without hitting rate limits.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path


def test_scraping_speed(
    num_events: int = 5,
    download_delay: float = 2.0,
    wait_timeout: int = 6000,
):
    """
    Test scraping speed with specific delay settings.

    Args:
        num_events: Number of events to test (default: 5)
        download_delay: Scrapy DOWNLOAD_DELAY in seconds
        wait_timeout: Playwright wait_for_timeout in milliseconds
    """
    print(f"\n{'='*70}")
    print(f"🧪 SCRAPING SPEED TEST")
    print(f"{'='*70}")
    print(f"Settings:")
    print(f"  - Download delay: {download_delay}s")
    print(f"  - Wait timeout: {wait_timeout}ms ({wait_timeout/1000}s)")
    print(f"  - Test events: {num_events}")
    print(f"{'='*70}\n")

    # Load first N events from discovered list
    archive_file = Path("data/raw/bfo_numbered_events.jsonl")
    if not archive_file.exists():
        print(f"❌ Archive file not found: {archive_file}")
        return

    test_urls = []
    with archive_file.open() as f:
        for i, line in enumerate(f):
            if i >= num_events:
                break
            data = json.loads(line)
            test_urls.append(data["event_url"])

    print(f"📋 Testing with {len(test_urls)} events:")
    for i, url in enumerate(test_urls, 1):
        print(f"   {i}. {url}")
    print()

    # Create temp output file
    output_file = Path("data/raw/bfo_speed_test.jsonl")

    # Build scrapy command with custom settings
    cmd = [
        ".venv/bin/scrapy", "crawl", "bestfightodds_odds_final",
        "-a", f"event_urls={','.join(test_urls)}",
        "-a", f"wait_timeout={wait_timeout}",
        "-o", str(output_file),
        "-s", f"DOWNLOAD_DELAY={download_delay}",
    ]

    # Run scraper and measure time
    start_time = time.time()

    print(f"⏱️  Starting scrape at {time.strftime('%H:%M:%S')}")
    print(f"Running: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )

        end_time = time.time()
        elapsed = end_time - start_time

        print(f"\n{'='*70}")
        print(f"✅ TEST COMPLETE")
        print(f"{'='*70}")
        print(f"⏱️  Total time: {elapsed:.1f}s ({elapsed/60:.2f} minutes)")
        print(f"📊 Average per event: {elapsed/num_events:.1f}s")
        print(f"📈 Projected for 537 events: {(elapsed/num_events)*537/3600:.2f} hours")
        print(f"{'='*70}\n")

        # Check output
        if output_file.exists():
            with output_file.open() as f:
                lines = f.readlines()
                print(f"✅ Successfully scraped {len(lines)} fight records")
        else:
            print(f"⚠️  Output file not created")

        # Show any errors
        if result.returncode != 0:
            print(f"\n⚠️  Scraper exited with code {result.returncode}")
            if result.stderr:
                print(f"\nErrors:\n{result.stderr[-500:]}")  # Last 500 chars

        return {
            "elapsed_seconds": elapsed,
            "avg_per_event": elapsed / num_events,
            "projected_hours": (elapsed / num_events) * 537 / 3600,
            "settings": {
                "download_delay": download_delay,
                "wait_timeout": wait_timeout,
            }
        }

    except subprocess.TimeoutExpired:
        print(f"\n❌ Test timed out after 10 minutes")
        return None
    except Exception as e:
        print(f"\n❌ Error running test: {e}")
        return None


if __name__ == "__main__":
    import sys

    # Run test with conservative settings
    print("\n" + "="*70)
    print("TESTING CONSERVATIVE SETTINGS (recommended)")
    print("="*70)
    result = test_scraping_speed(
        num_events=5,
        download_delay=2.0,    # Down from 3.0
        wait_timeout=6000,     # Down from 8000
    )

    if result and len(sys.argv) > 1 and sys.argv[1] == "--aggressive":
        # Also test aggressive settings
        print("\n" + "="*70)
        print("TESTING AGGRESSIVE SETTINGS")
        print("="*70)
        test_scraping_speed(
            num_events=5,
            download_delay=1.5,    # Down from 3.0
            wait_timeout=4000,     # Down from 8000
        )

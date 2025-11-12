#!/usr/bin/env python3
"""
Batch scraping script for UFC historical line movement (betting odds trends).

WARNING: This is MUCH slower than closing odds scraping!
- Each event takes 5-15 minutes (vs 15 seconds for closing odds)
- Full 537 events: ~40-73 hours (vs 2.2 hours)

This script:
1. Loads events from archive
2. Checks which events have already been scraped
3. Scrapes remaining events in batches
4. Tracks progress and estimates time remaining
5. Handles failures and retries

Usage:
    # Test with 1 event first (recommended!)
    python scripts/batch_scrape_line_movement.py --test

    # Scrape recent events only (2020-2025)
    python scripts/batch_scrape_line_movement.py --organization UFC --batch-size 10 --recent-only

    # Full scrape (537 events, ~73 hours)
    python scripts/batch_scrape_line_movement.py --organization UFC --batch-size 10

    # Resume previous session
    python scripts/batch_scrape_line_movement.py --resume
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


class BatchLineMovementScraper:
    """Manages batch scraping of historical line movement."""

    def __init__(
        self,
        archive_file: str = "data/raw/bfo_numbered_events.jsonl",
        output_file: str = "data/raw/bfo_line_movement_batch.jsonl",
        progress_file: str = "data/raw/.line_movement_progress.json",
        organization: str = None,
        batch_size: int = 10,
        download_delay: float = 4.0,
        wait_timeout: int = 8000,
        click_wait: int = 2000,
        recent_only: bool = False,
    ):
        self.archive_file = Path(archive_file)
        self.output_file = Path(output_file)
        self.progress_file = Path(progress_file)
        self.organization = organization
        self.batch_size = batch_size
        self.download_delay = download_delay
        self.wait_timeout = wait_timeout
        self.click_wait = click_wait
        self.recent_only = recent_only

        # Stats
        self.total_events = 0
        self.scraped_events = 0
        self.failed_events = []
        self.start_time = None

    def load_events(self) -> list[dict]:
        """Load events from archive file."""
        if not self.archive_file.exists():
            print(f"❌ Archive file not found: {self.archive_file}")
            print("   Run: make discover-events first")
            sys.exit(1)

        events = []
        with self.archive_file.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)

                    # Filter by organization if specified
                    if self.organization:
                        if event.get("organization", "").upper() != self.organization.upper():
                            continue

                    # Filter by date if recent_only
                    if self.recent_only:
                        event_date_str = event.get("event_date", "")
                        try:
                            # Parse date (format: "Feb 8th 2025")
                            from dateutil import parser
                            event_date = parser.parse(event_date_str)
                            if event_date.year < 2020:
                                continue
                        except:
                            # If can't parse date, skip filtering
                            pass

                    events.append(event)

                except json.JSONDecodeError:
                    continue

        print(f"📋 Loaded {len(events)} events from archive")
        if self.organization:
            print(f"   Filtered for: {self.organization}")
        if self.recent_only:
            print(f"   Recent only: 2020-2025")

        return events

    def load_progress(self) -> dict:
        """Load previous progress if exists."""
        if self.progress_file.exists():
            with self.progress_file.open() as f:
                return json.load(f)
        return {"scraped": [], "failed": []}

    def save_progress(self, scraped: list[str], failed: list[str]):
        """Save current progress."""
        progress = {
            "scraped": scraped,
            "failed": failed,
            "last_updated": datetime.utcnow().isoformat(),
        }
        with self.progress_file.open("w") as f:
            json.dump(progress, f, indent=2)

    def run(self, dry_run: bool = False, resume: bool = False, test: bool = False):
        """Run batch scraping."""
        print("\n" + "="*70)
        print("📈 BATCH LINE MOVEMENT SCRAPING")
        print("="*70)

        # Load events
        events = self.load_events()
        self.total_events = len(events)

        if self.total_events == 0:
            print("\n❌ No events to scrape")
            return

        # Load progress
        progress = self.load_progress()
        scraped = progress.get("scraped", [])
        failed = progress.get("failed", [])

        # Filter out already scraped events
        remaining = [
            e for e in events
            if e.get("event_id") not in scraped and e.get("event_slug") not in scraped
        ]

        print(f"\n📊 Progress:")
        print(f"   Total events: {self.total_events}")
        print(f"   Already scraped: {len(scraped)}")
        print(f"   Failed: {len(failed)}")
        print(f"   Remaining: {len(remaining)}")

        if test:
            print(f"\n🧪 TEST MODE: Scraping 1 event only")
            remaining = remaining[:1]
        elif not remaining:
            print(f"\n✅ All events already scraped!")
            return

        # Estimate time (conservative: 8 minutes per event)
        est_minutes = len(remaining) * 8
        est_hours = est_minutes / 60
        print(f"\n⏱️  Estimated time: {est_minutes} minutes ({est_hours:.1f} hours)")
        print(f"   Per event: ~8 minutes (160 clicks × 3s)")
        print(f"   Settings: delay={self.download_delay}s, click_wait={self.click_wait}ms")

        if dry_run:
            print(f"\n🔍 DRY RUN - Would scrape {len(remaining)} events")
            for i, event in enumerate(remaining[:10], 1):
                print(f"   {i}. {event.get('event_title')} ({event.get('event_date')})")
            if len(remaining) > 10:
                print(f"   ... and {len(remaining) - 10} more")
            return

        # Confirm before starting (unless --resume or --test)
        if not resume and not test:
            print(f"\n⚠️  WARNING: This will take {est_hours:.1f} hours!")
            response = input(f"Continue? (yes/no): ")
            if response.lower() != "yes":
                print("Aborted")
                return

        print(f"\n🚀 Starting scrape...")
        self.start_time = time.time()

        # Process events in batches
        for batch_start in range(0, len(remaining), self.batch_size):
            batch = remaining[batch_start:batch_start + self.batch_size]
            batch_num = batch_start // self.batch_size + 1
            total_batches = (len(remaining) + self.batch_size - 1) // self.batch_size

            print(f"\n{'='*70}")
            print(f"📦 BATCH {batch_num}/{total_batches}")
            print(f"{'='*70}")

            for i, event in enumerate(batch, 1):
                event_title = event.get("event_title", "Unknown Event")
                event_date = event.get("event_date", "Unknown Date")
                event_url = event.get("event_url")
                event_id = event.get("event_id") or event.get("event_slug")

                if not event_url:
                    print(f"\n[{batch_start + i}/{len(remaining)}] ⚠️  Skipping (no URL): {event_title}")
                    continue

                print(f"\n[{batch_start + i}/{len(remaining)}] Scraping: {event_title}")
                print(f"   Date: {event_date}")
                print(f"   URL: {event_url}")

                try:
                    # Run scrapy command with configurable settings
                    cmd = [
                        ".venv/bin/scrapy",
                        "crawl",
                        "bestfightodds_line_movement",
                        "-a",
                        f"event_urls={event_url}",
                        "-o",
                        str(self.output_file),
                        "-s",
                        f"DOWNLOAD_DELAY={self.download_delay}",
                        "--loglevel=INFO",  # Show progress
                    ]

                    event_start = time.time()

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=1800,  # 30 minute timeout per event
                    )

                    event_time = time.time() - event_start

                    if result.returncode == 0:
                        print(f"   ✅ Success! ({event_time/60:.1f} minutes)")
                        scraped.append(event_id)
                    else:
                        print(f"   ❌ Failed (exit code: {result.returncode})")
                        failed.append(event_id)
                        if result.stderr:
                            print(f"   Error: {result.stderr[-200:]}")

                except subprocess.TimeoutExpired:
                    print(f"   ❌ Timeout (>30 minutes)")
                    failed.append(event_id)
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    failed.append(event_id)

                # Save progress after each event
                self.save_progress(scraped, failed)

                # Show stats
                elapsed = time.time() - self.start_time
                events_done = len(scraped) + len(failed) - len(progress.get("scraped", [])) - len(progress.get("failed", []))
                if events_done > 0:
                    avg_time = elapsed / events_done
                    remaining_events = len(remaining) - events_done
                    eta_seconds = remaining_events * avg_time
                    eta = timedelta(seconds=int(eta_seconds))

                    print(f"\n   ⏱️  Progress: {events_done}/{len(remaining)} events")
                    print(f"   ⏱️  Average: {avg_time/60:.1f} min/event")
                    print(f"   ⏱️  ETA: {eta}")

        # Final summary
        print(f"\n{'='*70}")
        print(f"✅ BATCH SCRAPING COMPLETE")
        print(f"{'='*70}")
        print(f"Total events: {len(remaining)}")
        print(f"Successfully scraped: {len(scraped) - len(progress.get('scraped', []))}")
        print(f"Failed: {len(failed) - len(progress.get('failed', []))}")
        print(f"Total time: {(time.time() - self.start_time)/3600:.2f} hours")

        if failed:
            print(f"\n⚠️  Failed events saved to progress file")
            print(f"   Run with --retry-failed to retry them")


def main():
    parser = argparse.ArgumentParser(
        description="Batch scrape UFC historical line movement (betting odds trends)"
    )
    parser.add_argument(
        "--organization",
        "-o",
        default="UFC",
        help="Organization to scrape (default: UFC)",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=10,
        help="Number of events per batch (default: 10)",
    )
    parser.add_argument(
        "--archive-file",
        default="data/raw/bfo_numbered_events.jsonl",
        help="Archive file path",
    )
    parser.add_argument(
        "--output-file",
        default="data/raw/bfo_line_movement_batch.jsonl",
        help="Output file path",
    )
    parser.add_argument(
        "--download-delay",
        type=float,
        default=4.0,
        help="Scrapy DOWNLOAD_DELAY in seconds (default: 4.0)",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=8000,
        help="Playwright wait timeout in milliseconds (default: 8000)",
    )
    parser.add_argument(
        "--click-wait",
        type=int,
        default=2000,
        help="Wait time after clicking odds cell in milliseconds (default: 2000)",
    )
    parser.add_argument(
        "--recent-only",
        action="store_true",
        help="Only scrape events from 2020-2025",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: scrape 1 event only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be scraped without actually scraping",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume previous scraping session without confirmation",
    )

    args = parser.parse_args()

    scraper = BatchLineMovementScraper(
        archive_file=args.archive_file,
        output_file=args.output_file,
        organization=args.organization,
        batch_size=args.batch_size,
        download_delay=args.download_delay,
        wait_timeout=args.wait_timeout,
        click_wait=args.click_wait,
        recent_only=args.recent_only,
    )

    scraper.run(
        dry_run=args.dry_run,
        resume=args.resume,
        test=args.test,
    )


if __name__ == "__main__":
    main()

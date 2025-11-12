#!/usr/bin/env python3
"""
Batch scraping script for UFC betting odds.

This script:
1. Loads events from archive
2. Checks which events have already been scraped
3. Scrapes remaining events in batches
4. Tracks progress and estimates time remaining
5. Handles failures and retries

Usage:
    python scripts/batch_scrape_odds.py --organization UFC --batch-size 10
    python scripts/batch_scrape_odds.py --organization UFC --resume
    python scripts/batch_scrape_odds.py --dry-run  # Show what would be scraped
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


class BatchOddsScraper:
    """Manages batch scraping of betting odds."""

    def __init__(
        self,
        archive_file: str = "data/raw/bfo_events_archive.jsonl",
        output_file: str = "data/raw/bfo_odds_batch.jsonl",
        progress_file: str = "data/raw/.scrape_progress.json",
        organization: str = None,
        batch_size: int = 10,
    ):
        self.archive_file = Path(archive_file)
        self.output_file = Path(output_file)
        self.progress_file = Path(progress_file)
        self.organization = organization
        self.batch_size = batch_size

        # Stats
        self.total_events = 0
        self.scraped_events = 0
        self.failed_events = []
        self.start_time = None

    def load_events(self) -> list[dict]:
        """Load events from archive file."""
        if not self.archive_file.exists():
            print(f"❌ Archive file not found: {self.archive_file}")
            print("   Run: make scrape-archive first")
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
                        if event.get("organization", "").upper() == self.organization.upper():
                            events.append(event)
                    else:
                        events.append(event)
                except json.JSONDecodeError:
                    continue

        print(f"📋 Loaded {len(events)} events from archive")
        if self.organization:
            print(f"   Filtered for: {self.organization}")

        return events

    def load_progress(self) -> dict:
        """Load scraping progress."""
        if not self.progress_file.exists():
            return {"scraped_event_ids": [], "failed_event_ids": [], "last_run": None}

        with self.progress_file.open() as f:
            return json.load(f)

    def save_progress(self, scraped_ids: list[str], failed_ids: list[str]):
        """Save scraping progress."""
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        progress = {
            "scraped_event_ids": scraped_ids,
            "failed_event_ids": failed_ids,
            "last_run": datetime.utcnow().isoformat(),
            "total_scraped": len(scraped_ids),
            "total_failed": len(failed_ids),
        }
        with self.progress_file.open("w") as f:
            json.dump(progress, f, indent=2)

    def get_pending_events(self, all_events: list[dict]) -> list[dict]:
        """Get events that haven't been scraped yet."""
        progress = self.load_progress()
        scraped_ids = set(progress.get("scraped_event_ids", []))

        # Support both event_id and event_slug as identifiers
        pending = [
            e for e in all_events
            if e.get("event_id", e.get("event_slug")) not in scraped_ids
        ]

        print(f"✅ Already scraped: {len(scraped_ids)} events")
        print(f"📥 Pending: {len(pending)} events")

        return pending

    def scrape_batch(self, events: list[dict]) -> tuple[list[str], list[str]]:
        """Scrape a batch of events."""
        scraped = []
        failed = []

        for i, event in enumerate(events, 1):
            # Support both event_id and event_slug
            event_id = event.get("event_id", event.get("event_slug"))
            event_url = event.get("event_url")
            event_title = event.get("event_title", event.get("event_title_guess", "Unknown"))

            print(f"\n[{i}/{len(events)}] Scraping: {event_title}")
            print(f"   URL: {event_url}")

            try:
                # Run scrapy command
                cmd = [
                    ".venv/bin/scrapy",
                    "crawl",
                    "bestfightodds_odds_final",
                    "-a",
                    f"event_urls={event_url}",
                    "-o",
                    str(self.output_file),
                    "--loglevel=ERROR",  # Quiet output
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minute timeout per event
                )

                if result.returncode == 0:
                    print(f"   ✅ Success!")
                    scraped.append(event_id)
                else:
                    print(f"   ❌ Failed: {result.stderr[:200]}")
                    failed.append(event_id)

            except subprocess.TimeoutExpired:
                print(f"   ⏱️  Timeout after 2 minutes")
                failed.append(event_id)
            except Exception as e:
                print(f"   ❌ Error: {e}")
                failed.append(event_id)

            # Small delay between events
            if i < len(events):
                time.sleep(2)

        return scraped, failed

    def estimate_time(self, num_events: int, avg_time_per_event: int = 15) -> str:
        """Estimate time to scrape remaining events."""
        total_seconds = num_events * avg_time_per_event
        td = timedelta(seconds=total_seconds)

        hours = td.seconds // 3600
        minutes = (td.seconds % 3600) // 60
        days = td.days

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def run(self, dry_run: bool = False, resume: bool = False):
        """Run batch scraping."""
        print("=" * 70)
        print("🕷️  BATCH ODDS SCRAPER")
        print("=" * 70)

        # Load events
        all_events = self.load_events()
        self.total_events = len(all_events)

        if self.total_events == 0:
            print("❌ No events to scrape!")
            return

        # Get pending events
        pending_events = self.get_pending_events(all_events)

        if len(pending_events) == 0:
            print("\n✅ All events already scraped!")
            return

        # Show estimate
        estimate = self.estimate_time(len(pending_events))
        print(f"\n⏱️  Estimated time: {estimate}")
        print(f"   ({len(pending_events)} events × ~15 seconds each)")

        if dry_run:
            print("\n🔍 DRY RUN - Would scrape:")
            for event in pending_events[:10]:
                title = event.get('event_title', event.get('event_title_guess', 'Unknown'))
                date = event.get('event_date', 'Unknown date')
                url = event.get('event_url', '')
                print(f"   - {title} ({date})")
                print(f"     {url}")
            if len(pending_events) > 10:
                print(f"   ... and {len(pending_events) - 10} more")
            return

        # Confirm before starting
        if not resume:
            response = input(f"\n▶️  Start scraping {len(pending_events)} events? [y/N]: ")
            if response.lower() != "y":
                print("❌ Cancelled")
                return

        # Start scraping
        print(f"\n🚀 Starting batch scrape...")
        self.start_time = time.time()

        # Load existing progress
        progress = self.load_progress()
        all_scraped = progress.get("scraped_event_ids", [])
        all_failed = progress.get("failed_event_ids", [])

        # Process in batches
        for batch_num, i in enumerate(range(0, len(pending_events), self.batch_size), 1):
            batch = pending_events[i : i + self.batch_size]

            print(f"\n{'='*70}")
            print(f"📦 BATCH {batch_num}/{(len(pending_events) + self.batch_size - 1) // self.batch_size}")
            print(f"{'='*70}")

            scraped, failed = self.scrape_batch(batch)

            # Update totals
            all_scraped.extend(scraped)
            all_failed.extend(failed)

            # Save progress after each batch
            self.save_progress(all_scraped, all_failed)

            print(f"\n📊 Batch {batch_num} complete:")
            print(f"   ✅ Scraped: {len(scraped)}/{len(batch)}")
            print(f"   ❌ Failed: {len(failed)}/{len(batch)}")

            # Show overall progress
            total_done = len(all_scraped) + len(all_failed)
            progress_pct = (total_done / self.total_events) * 100
            print(f"\n📈 Overall Progress: {total_done}/{self.total_events} ({progress_pct:.1f}%)")

            # Time estimate for remaining
            if total_done > 0:
                elapsed = time.time() - self.start_time
                avg_time = elapsed / total_done
                remaining = self.total_events - total_done
                eta_seconds = remaining * avg_time
                eta = timedelta(seconds=int(eta_seconds))
                print(f"   ⏱️  ETA: {eta}")

        # Final summary
        elapsed = time.time() - self.start_time
        print(f"\n{'='*70}")
        print("🎉 BATCH SCRAPING COMPLETE!")
        print(f"{'='*70}")
        print(f"✅ Scraped: {len(all_scraped)} events")
        print(f"❌ Failed: {len(all_failed)} events")
        print(f"⏱️  Time: {timedelta(seconds=int(elapsed))}")
        print(f"📁 Output: {self.output_file}")

        if all_failed:
            print(f"\n⚠️  Failed events saved to progress file")
            print(f"   Run with --retry-failed to retry them")


def main():
    parser = argparse.ArgumentParser(description="Batch scrape UFC betting odds")
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
        default="data/raw/bfo_events_archive.jsonl",
        help="Archive file path",
    )
    parser.add_argument(
        "--output-file",
        default="data/raw/bfo_odds_batch.jsonl",
        help="Output file path",
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

    scraper = BatchOddsScraper(
        archive_file=args.archive_file,
        output_file=args.output_file,
        organization=args.organization,
        batch_size=args.batch_size,
    )

    scraper.run(dry_run=args.dry_run, resume=args.resume)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Batch scrape mean odds from BestFightOdds fighter pages.

This script:
1. Loads the corrected fighter URL mapping
2. Runs the spider in batches to avoid overwhelming the site
3. Tracks progress and allows resuming from where it left off
4. Provides time estimates

Usage:
    # Full scrape (all 1,262 fighters)
    python scripts/scrape_bfo_fighter_mean_odds.py

    # Test with first 10 fighters
    python scripts/scrape_bfo_fighter_mean_odds.py --limit 10

    # Resume from fighter 500
    python scripts/scrape_bfo_fighter_mean_odds.py --start 500

    # Custom batch size
    python scripts/scrape_bfo_fighter_mean_odds.py --batch-size 50
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


def load_fighter_urls(mapping_file: Path, start: int = 0, limit: int | None = None) -> list[str]:
    """Load fighter URLs from corrected mapping file."""
    urls = []
    with mapping_file.open() as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            if bfo_url := data.get("bfo_url"):
                urls.append(bfo_url)

    # Apply start/limit
    if limit:
        urls = urls[start : start + limit]
    else:
        urls = urls[start:]

    return urls


def run_spider_batch(urls: list[str], output_file: Path, batch_num: int, total_batches: int) -> tuple[bool, int]:
    """
    Run spider for a batch of fighter URLs.

    Returns:
        (success: bool, items_scraped: int)
    """
    print(f"\n{'=' * 80}")
    print(f"Batch {batch_num}/{total_batches}: {len(urls)} fighters")
    print(f"{'=' * 80}")

    # Count items before this batch
    items_before = 0
    if output_file.exists():
        with output_file.open() as f:
            items_before = sum(1 for _ in f)

    # Join URLs with commas for the spider argument
    urls_arg = ",".join(urls)

    # Run the spider
    cmd = [
        ".venv/bin/scrapy",
        "crawl",
        "bestfightodds_fighter_mean_odds",
        "-a",
        f"fighter_urls={urls_arg}",
        "-o",
        str(output_file),
    ]

    start_time = time.time()

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)
        elapsed = time.time() - start_time

        # Count items after this batch
        items_after = 0
        if output_file.exists():
            with output_file.open() as f:
                items_after = sum(1 for _ in f)

        items_scraped = items_after - items_before

        print(f"✓ Batch completed in {elapsed:.1f}s ({elapsed / len(urls):.1f}s per fighter)")
        print(f"  Scraped {items_scraped} fight records ({items_after} total in file)")

        return True, items_scraped

    except subprocess.TimeoutExpired:
        print(f"✗ Batch timed out after 600s")
        return False, 0
    except subprocess.CalledProcessError as e:
        print(f"✗ Batch failed with error: {e}")
        print(f"  stderr: {e.stderr}")
        return False, 0


def main():
    parser = argparse.ArgumentParser(description="Batch scrape BestFightOdds fighter mean odds")
    parser.add_argument(
        "--mapping-file",
        type=Path,
        default=Path("data/processed/bfo_fighter_url_mapping_corrected.jsonl"),
        help="Path to fighter URL mapping file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/bfo_fighter_mean_odds.jsonl"),
        help="Output file for scraped data",
    )
    parser.add_argument("--start", type=int, default=0, help="Start from fighter index (for resuming)")
    parser.add_argument("--limit", type=int, help="Limit total fighters to scrape (for testing)")
    parser.add_argument(
        "--batch-size", type=int, default=20, help="Number of fighters to scrape per batch (default: 20)"
    )

    args = parser.parse_args()

    # Load fighter URLs
    print(f"Loading fighter URLs from {args.mapping_file}...")
    all_urls = load_fighter_urls(args.mapping_file, start=args.start, limit=args.limit)

    print(f"Found {len(all_urls)} fighters to scrape")
    if args.start > 0:
        print(f"  Starting from index {args.start}")
    if args.limit:
        print(f"  Limited to {args.limit} fighters")

    # Calculate batches
    batches = []
    for i in range(0, len(all_urls), args.batch_size):
        batches.append(all_urls[i : i + args.batch_size])

    print(f"\nProcessing in {len(batches)} batches of {args.batch_size} fighters")

    # Estimate time (based on ~8s per fighter from testing)
    estimated_seconds = len(all_urls) * 8
    estimated_time = timedelta(seconds=estimated_seconds)
    estimated_end = datetime.now() + estimated_time

    print(f"Estimated time: {estimated_time}")
    print(f"Estimated completion: {estimated_end.strftime('%Y-%m-%d %H:%M:%S')}")

    # Confirm before starting
    if len(all_urls) > 50:
        response = input("\nProceed with scraping? [y/N] ")
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    # Run batches
    overall_start = time.time()
    total_items = 0
    successful_batches = 0

    for batch_num, batch_urls in enumerate(batches, 1):
        success, items = run_spider_batch(batch_urls, args.output, batch_num, len(batches))

        if success:
            successful_batches += 1
            total_items += items
        else:
            print(f"\n⚠️  Batch {batch_num} failed - continuing with next batch")

        # Progress update
        elapsed = time.time() - overall_start
        fighters_done = (batch_num - 1) * args.batch_size + len(batch_urls)
        avg_time_per_fighter = elapsed / fighters_done
        remaining_fighters = len(all_urls) - fighters_done
        eta_seconds = remaining_fighters * avg_time_per_fighter
        eta = datetime.now() + timedelta(seconds=eta_seconds)

        print(f"\n📊 Progress: {fighters_done}/{len(all_urls)} fighters ({fighters_done / len(all_urls) * 100:.1f}%)")
        print(f"   Total items scraped: {total_items}")
        print(f"   Average: {avg_time_per_fighter:.1f}s per fighter")
        print(f"   ETA: {eta.strftime('%Y-%m-%d %H:%M:%S')}")

        # Delay between batches (be respectful)
        if batch_num < len(batches):
            delay = 3
            print(f"   Waiting {delay}s before next batch...")
            time.sleep(delay)

    # Final summary
    overall_elapsed = time.time() - overall_start
    print(f"\n{'=' * 80}")
    print(f"Scraping completed!")
    print(f"{'=' * 80}")
    print(f"Total time: {timedelta(seconds=int(overall_elapsed))}")
    print(f"Successful batches: {successful_batches}/{len(batches)}")
    print(f"Total items scraped: {total_items}")
    print(f"Average: {overall_elapsed / len(all_urls):.1f}s per fighter")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()

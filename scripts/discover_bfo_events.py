#!/usr/bin/env python3
"""
Discover BestFightOdds UFC event URLs using web search.

This script uses Google search to discover historical UFC event pages
on BestFightOdds.com, building a comprehensive list of event URLs
for scraping.

Strategy:
1. Search by year: "site:bestfightodds.com/events ufc 2020"
2. Search by numbered events: "site:bestfightodds.com/events ufc 100"
3. Search by month/year: "site:bestfightodds.com/events ufc january 2020"
4. Extract unique event URLs from all results
5. Save to JSONL for use with archive spider

Usage:
    python scripts/discover_bfo_events.py
    python scripts/discover_bfo_events.py --years 2020-2025
    python scripts/discover_bfo_events.py --output data/raw/bfo_discovered_events.jsonl
"""

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Generator

# Note: This script assumes WebSearch functionality is available
# If running standalone, you'll need to implement web search or use an API


class EventURLDiscoverer:
    """Discover UFC event URLs on BestFightOdds using web search."""

    def __init__(self, output_file: Path):
        self.output_file = output_file
        self.discovered_urls: set[str] = set()
        self.events: list[dict] = []

    def search_by_year(self, year: int) -> list[str]:
        """
        Search for UFC events from a specific year.

        Args:
            year: Year to search for (e.g., 2020)

        Returns:
            List of URLs found in search results
        """
        queries = [
            f"site:bestfightodds.com/events ufc {year}",
            f"site:bestfightodds.com/events ufc {year} fight night",
            f"site:bestfightodds.com/events ufc on espn {year}",
        ]

        urls = []
        for query in queries:
            print(f"  Searching: {query}")
            # In actual implementation, this would use WebSearch
            # For now, this is a placeholder that would be replaced
            # with actual search functionality
            search_urls = self._placeholder_search(query)
            urls.extend(search_urls)
            time.sleep(2)  # Rate limiting

        return urls

    def search_by_numbered_events(self, start: int = 1, end: int = 325) -> list[str]:
        """
        Search for numbered UFC events (UFC 1, UFC 2, etc.).

        Args:
            start: Starting UFC number
            end: Ending UFC number (UFC 322 was Nov 2025)

        Returns:
            List of URLs found
        """
        urls = []

        # Search in batches to avoid too many individual searches
        # Search major milestone events
        milestones = list(range(1, end + 1, 10))  # Every 10th event
        milestones.extend([100, 150, 200, 250, 300])  # Major milestones

        for ufc_num in sorted(set(milestones)):
            if ufc_num > end:
                continue

            query = f"site:bestfightodds.com/events ufc {ufc_num}"
            print(f"  Searching: UFC {ufc_num}")

            search_urls = self._placeholder_search(query)
            urls.extend(search_urls)
            time.sleep(1)  # Rate limiting

        return urls

    def search_by_month(self, year: int, month: str) -> list[str]:
        """
        Search for UFC events by month and year.

        Args:
            year: Year to search
            month: Month name (e.g., "January")

        Returns:
            List of URLs found
        """
        query = f"site:bestfightodds.com/events ufc {month} {year}"
        print(f"  Searching: {month} {year}")
        return self._placeholder_search(query)

    def _placeholder_search(self, query: str) -> list[str]:
        """
        Placeholder for web search functionality.

        In actual implementation, this would use WebSearch tool
        or a search API to find URLs matching the query.

        Args:
            query: Search query

        Returns:
            List of BestFightOdds event URLs
        """
        # This is a placeholder that would be replaced with actual search
        # When integrated with Claude Code's WebSearch tool
        return []

    def extract_event_metadata(self, url: str) -> dict | None:
        """
        Extract event metadata from URL.

        URL format: https://www.bestfightodds.com/events/ufc-247-jones-vs-reyes-1837

        Args:
            url: BestFightOdds event URL

        Returns:
            Dictionary with event metadata or None if invalid
        """
        match = re.search(r'/events/([^/]+)-(\d+)$', url)
        if not match:
            return None

        slug = match.group(1)
        numeric_id = match.group(2)

        # Extract event title from slug
        title_parts = slug.split('-')
        # Capitalize and join
        title = ' '.join(word.capitalize() for word in title_parts)

        return {
            "event_url": url,
            "event_slug": f"{slug}-{numeric_id}",
            "event_numeric_id": int(numeric_id),
            "event_title_guess": title,  # Guess from slug
            "discovered_at": datetime.utcnow().isoformat(),
        }

    def deduplicate_and_save(self):
        """Deduplicate discovered URLs and save to file."""
        print(f"\n📊 Deduplicating {len(self.events)} events...")

        # Deduplicate by URL
        seen_urls = set()
        unique_events = []

        for event in self.events:
            if event["event_url"] not in seen_urls:
                seen_urls.add(event["event_url"])
                unique_events.append(event)

        print(f"✅ Found {len(unique_events)} unique events")

        # Sort by numeric ID
        unique_events.sort(key=lambda x: x["event_numeric_id"])

        # Save to file
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, 'w') as f:
            for event in unique_events:
                f.write(json.dumps(event) + '\n')

        print(f"💾 Saved to {self.output_file}")

        # Print statistics
        print(f"\n📈 Statistics:")
        print(f"   Total URLs discovered: {len(self.discovered_urls)}")
        print(f"   Unique events: {len(unique_events)}")
        if unique_events:
            print(f"   ID range: {unique_events[0]['event_numeric_id']} - "
                  f"{unique_events[-1]['event_numeric_id']}")

    def discover_all(self, start_year: int = 2007, end_year: int = 2025):
        """
        Run complete discovery process.

        Args:
            start_year: Starting year for search
            end_year: Ending year for search
        """
        print("=" * 70)
        print("🔍 UFC EVENT URL DISCOVERY")
        print("=" * 70)
        print(f"Searching BestFightOdds for UFC events ({start_year}-{end_year})")
        print()

        all_urls = []

        # Search by year
        print("1️⃣  Searching by year...")
        for year in range(start_year, end_year + 1):
            print(f"\n📅 Year: {year}")
            urls = self.search_by_year(year)
            all_urls.extend(urls)

        # Search by numbered events
        print("\n2️⃣  Searching numbered UFC events...")
        urls = self.search_by_numbered_events(start=1, end=325)
        all_urls.extend(urls)

        # Extract metadata from all URLs
        print("\n3️⃣  Extracting event metadata...")
        for url in all_urls:
            if url not in self.discovered_urls:
                self.discovered_urls.add(url)
                metadata = self.extract_event_metadata(url)
                if metadata:
                    self.events.append(metadata)

        # Save results
        self.deduplicate_and_save()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Discover UFC event URLs on BestFightOdds.com"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/raw/bfo_discovered_events.jsonl"),
        help="Output file for discovered events",
    )
    parser.add_argument(
        "--years",
        type=str,
        help="Year range to search (e.g., '2020-2025')",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode - search only 2024-2025",
    )

    args = parser.parse_args()

    # Determine year range
    if args.test:
        start_year, end_year = 2024, 2025
    elif args.years:
        try:
            start_year, end_year = map(int, args.years.split('-'))
        except ValueError:
            print("Error: --years format should be 'START-END' (e.g., '2020-2025')")
            return 1
    else:
        start_year, end_year = 2007, 2025

    # Run discovery
    discoverer = EventURLDiscoverer(args.output)
    discoverer.discover_all(start_year, end_year)

    return 0


if __name__ == "__main__":
    exit(main())

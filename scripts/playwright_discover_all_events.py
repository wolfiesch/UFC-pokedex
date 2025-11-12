#!/usr/bin/env python3
"""
Use Playwright to discover all UFC events from BestFightOdds.com archive.

The archive search returns 771 total UFC events but limits to 25 per search.
This script searches year-by-year and month-by-month to extract all events.

Usage:
    python scripts/playwright_discover_all_events.py
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright


async def search_and_extract(page, query: str) -> list[dict]:
    """
    Search for events and extract results.

    Args:
        page: Playwright page object
        query: Search query (e.g., "UFC 2024")

    Returns:
        List of event dictionaries
    """
    print(f"  Searching: {query}")

    # Navigate to archive
    await page.goto("https://www.bestfightodds.com/archive")
    await page.wait_for_load_state("networkidle")

    # Fill search box and submit
    search_box = page.locator('#page-content').get_by_role('textbox')
    await search_box.fill(query)
    await search_box.press('Enter')
    await page.wait_for_load_state("networkidle")

    # Wait for results
    await page.wait_for_timeout(2000)

    # Extract event URLs
    events = await page.evaluate("""
        () => {
            const eventLinks = Array.from(document.querySelectorAll('a[href*="/events/"]'));
            const ufcEvents = eventLinks.filter(link => {
                const row = link.closest('tr');
                return row && row.textContent.includes('UFC');
            });

            return ufcEvents.map(link => ({
                url: link.href,
                title: link.textContent.trim(),
                date: link.closest('tr')?.querySelector('td:first-child')?.textContent.trim()
            }));
        }
    """)

    print(f"    Found {len(events)} UFC events")
    return events


async def main():
    """Main discovery function."""
    print("=" * 70)
    print("🔍 PLAYWRIGHT UFC EVENT DISCOVERY")
    print("=" * 70)
    print()

    all_events = []
    seen_urls = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Strategy 1: Search by year (2007-2025)
            print("1️⃣  Searching by year...")
            for year in range(2007, 2026):
                events = await search_and_extract(page, f"UFC {year}")

                # Deduplicate
                for event in events:
                    if event['url'] not in seen_urls:
                        seen_urls.add(event['url'])

                        # Extract event ID from URL
                        url_parts = event['url'].split('/')
                        slug = url_parts[-1]
                        numeric_id = slug.split('-')[-1]

                        all_events.append({
                            "event_url": event['url'],
                            "event_slug": slug,
                            "event_numeric_id": int(numeric_id) if numeric_id.isdigit() else None,
                            "event_title": event['title'],
                            "event_date": event['date'],
                            "organization": "UFC",
                            "discovered_at": datetime.utcnow().isoformat(),
                        })

                await asyncio.sleep(1)  # Rate limiting

            # Strategy 2: Search specific terms for events that might be missed
            print("\n2️⃣  Searching specific terms...")
            search_terms = [
                "UFC Fight Night",
                "UFC on ESPN",
                "UFC on Fox",
                "UFC on FX",
                "UFC on Fuel",
                "The Ultimate Fighter",
                "UFC Apex",
                "UFC Vegas",
            ]

            for term in search_terms:
                events = await search_and_extract(page, term)

                for event in events:
                    if event['url'] not in seen_urls:
                        seen_urls.add(event['url'])

                        url_parts = event['url'].split('/')
                        slug = url_parts[-1]
                        numeric_id = slug.split('-')[-1]

                        all_events.append({
                            "event_url": event['url'],
                            "event_slug": slug,
                            "event_numeric_id": int(numeric_id) if numeric_id.isdigit() else None,
                            "event_title": event['title'],
                            "event_date": event['date'],
                            "organization": "UFC",
                            "discovered_at": datetime.utcnow().isoformat(),
                        })

                await asyncio.sleep(1)

        finally:
            await browser.close()

    # Sort by numeric ID
    all_events.sort(key=lambda x: x.get('event_numeric_id', 0))

    # Save results
    output_file = Path("data/raw/bfo_playwright_discovered_events.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        for event in all_events:
            f.write(json.dumps(event) + '\n')

    # Print summary
    print()
    print("=" * 70)
    print("✅ DISCOVERY COMPLETE")
    print("=" * 70)
    print(f"Total unique events discovered: {len(all_events)}")
    print(f"Saved to: {output_file}")

    if all_events:
        print(f"\nID range: {all_events[0]['event_numeric_id']} - {all_events[-1]['event_numeric_id']}")
        print(f"Date range: {all_events[0]['event_date']} - {all_events[-1]['event_date']}")

        print("\n📊 Sample events:")
        for event in all_events[:5]:
            print(f"  - {event['event_title']} ({event['event_date']}) - ID {event['event_numeric_id']}")

    print()
    return len(all_events)


if __name__ == "__main__":
    asyncio.run(main())

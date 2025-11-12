#!/usr/bin/env python3
"""
Complete UFC event discovery using month-by-month search strategy.

Since searches are limited to 25 results, we search by specific months
to ensure we capture all 771 UFC events.

Usage:
    python scripts/playwright_discover_complete.py
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright


async def search_and_extract(page, query: str) -> list[dict]:
    """Search for events and extract results."""
    await page.goto("https://www.bestfightodds.com/archive")
    await page.wait_for_load_state("networkidle")

    search_box = page.locator('#page-content').get_by_role('textbox')
    await search_box.fill(query)
    await search_box.press('Enter')
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(1500)

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

    return events


async def main():
    """Main discovery function with month-by-month search."""
    print("=" * 70)
    print("🔍 COMPLETE PLAYWRIGHT UFC EVENT DISCOVERY")
    print("=" * 70)
    print()

    all_events = []
    seen_urls = set()

    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Search month-by-month for each year
            print("🗓️  Searching month-by-month (2007-2025)...")
            total_queries = 0

            for year in range(2007, 2026):
                print(f"\n📅 Year {year}:")
                year_events_count = 0

                for month in months:
                    query = f"UFC {month} {year}"
                    events = await search_and_extract(page, query)
                    total_queries += 1

                    new_events = 0
                    for event in events:
                        if event['url'] not in seen_urls:
                            seen_urls.add(event['url'])
                            new_events += 1
                            year_events_count += 1

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

                    if new_events > 0:
                        print(f"  {month}: +{new_events} events")

                    await asyncio.sleep(0.5)  # Reduced sleep for faster execution

                print(f"  ✅ {year}: {year_events_count} events")

        finally:
            await browser.close()

    # Sort by numeric ID
    all_events.sort(key=lambda x: x.get('event_numeric_id', 0))

    # Save results
    output_file = Path("data/raw/bfo_all_events_complete.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        for event in all_events:
            f.write(json.dumps(event) + '\n')

    # Print summary
    print()
    print("=" * 70)
    print("✅ COMPLETE DISCOVERY FINISHED")
    print("=" * 70)
    print(f"Total searches performed: {total_queries}")
    print(f"Total unique events discovered: {len(all_events)}")
    print(f"Target: 771 UFC events")
    print(f"Coverage: {len(all_events)/771*100:.1f}%")
    print(f"Saved to: {output_file}")

    if all_events:
        print(f"\n📊 Statistics:")
        print(f"  ID range: {all_events[0]['event_numeric_id']} - {all_events[-1]['event_numeric_id']}")
        print(f"  Date range: {all_events[0]['event_date']} - {all_events[-1]['event_date']}")

        print("\n🎯 First 5 events:")
        for event in all_events[:5]:
            print(f"  - {event['event_title']} ({event['event_date']}) - ID {event['event_numeric_id']}")

        print("\n🎯 Last 5 events:")
        for event in all_events[-5:]:
            print(f"  - {event['event_title']} ({event['event_date']}) - ID {event['event_numeric_id']}")

    print()
    return len(all_events)


if __name__ == "__main__":
    total = asyncio.run(main())
    print(f"🎉 Discovered {total} UFC events!")

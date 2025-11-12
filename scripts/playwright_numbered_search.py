#!/usr/bin/env python3
"""
Search for all UFC events using numbered UFC events strategy.

This searches:
- UFC 1 through UFC 325 (all numbered events)
- Specific series: Fight Night, Vegas, Apex, ESPN, Fox
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright


async def search_and_extract(page, query: str) -> list[dict]:
    """Search and extract UFC events."""
    await page.goto("https://www.bestfightodds.com/archive", wait_until="networkidle")

    search_box = page.locator('#page-content').get_by_role('textbox')
    await search_box.fill(query)
    await search_box.press('Enter')
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(1000)

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
    """Main numbered search strategy."""
    print("=" * 70)
    print("🔢 NUMBERED UFC EVENT DISCOVERY")
    print("=" * 70)
    print()

    all_events = []
    seen_urls = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Strategy 1: Numbered UFC events (UFC 1-325)
            print("1️⃣  Searching numbered UFC events (1-325)...")
            for num in range(1, 326):
                if num % 10 == 0:
                    print(f"   Progress: UFC {num}")

                query = f"UFC {num}"
                events = await search_and_extract(page, query)

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

                await asyncio.sleep(0.3)  # Rate limiting

            print(f"   ✅ Found {len(all_events)} unique events from numbered search")

            # Strategy 2: Series searches
            print("\n2️⃣  Searching UFC series...")
            series = [
                ("UFC Fight Night", 30),  # Search multiple pages
                ("UFC Vegas", 5),
                ("UFC Apex", 3),
                ("UFC on ESPN", 20),
                ("UFC on Fox", 15),
                ("UFC on FX", 5),
                ("UFC on Fuel", 5),
                ("Ultimate Fighter Finale", 15),
            ]

            for series_name, search_count in series:
                print(f"   Searching: {series_name}...")
                initial_count = len(all_events)

                # Search with different variations
                for i in range(search_count):
                    query = f"{series_name} {i}" if i > 0 else series_name
                    events = await search_and_extract(page, query)

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

                    await asyncio.sleep(0.3)

                new_events = len(all_events) - initial_count
                print(f"      +{new_events} new events")

        finally:
            await browser.close()

    # Sort and save
    all_events.sort(key=lambda x: x.get('event_numeric_id', 0))

    output_file = Path("data/raw/bfo_numbered_events.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        for event in all_events:
            f.write(json.dumps(event) + '\n')

    # Summary
    print()
    print("=" * 70)
    print("✅ NUMBERED SEARCH COMPLETE")
    print("=" * 70)
    print(f"Total unique events: {len(all_events)}")
    print(f"Target: 772 UFC events")
    print(f"Coverage: {len(all_events)/772*100:.1f}%")
    print(f"Saved to: {output_file}")

    if all_events:
        print(f"\nID range: {all_events[0]['event_numeric_id']} - {all_events[-1]['event_numeric_id']}")
        print(f"Date range: {all_events[0]['event_date']} - {all_events[-1]['event_date']}")

    print()
    return len(all_events)


if __name__ == "__main__":
    total = asyncio.run(main())
    print(f"🎉 Discovered {total} UFC events!")

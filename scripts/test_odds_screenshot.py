#!/usr/bin/env python3
"""
Test script to take a screenshot of Best Fight Odds page
to verify if odds values are actually visible in the rendered page.
"""

import asyncio
from playwright.async_api import async_playwright


async def take_screenshot():
    """Take a screenshot of a UFC event page to see if odds are visible."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Use headless=False to see what's happening
        page = await browser.new_page()

        print("📱 Navigating to UFC Vegas 110 event page...")
        await page.goto("https://www.bestfightodds.com/events/ufc-vegas-110-3913")

        print("⏳ Waiting for page to load...")
        await page.wait_for_load_state("networkidle", timeout=15000)

        print("⏳ Waiting extra time for odds to load...")
        await page.wait_for_timeout(8000)  # Wait 8 seconds for odds to populate

        print("📸 Taking full page screenshot...")
        await page.screenshot(path="data/screenshots/bfo_full_page.png", full_page=True)

        print("📸 Taking viewport screenshot...")
        await page.screenshot(path="data/screenshots/bfo_viewport.png")

        # Try to find any odds cells
        print("\n🔍 Looking for odds in the page...")
        odds_cells = await page.query_selector_all("td")

        if odds_cells:
            print(f"   Found {len(odds_cells)} <td> elements")
            # Get text from first 10 cells
            for i, cell in enumerate(odds_cells[:10]):
                text = await cell.inner_text()
                print(f"   Cell {i}: '{text}'")
        else:
            print("   No <td> elements found!")

        # Check for data-bookie attributes
        print("\n🔍 Looking for data-bookie attributes...")
        bookie_cells = await page.query_selector_all("[data-bookie]")
        print(f"   Found {len(bookie_cells)} elements with data-bookie")

        # Get the HTML of the first matchup
        print("\n📋 HTML of first matchup row:")
        first_matchup = await page.query_selector("#mu-40336")
        if first_matchup:
            html = await first_matchup.evaluate("el => el.outerHTML")
            print(html[:500])  # First 500 chars

        print("\n✅ Screenshots saved to data/screenshots/")
        print("   - bfo_full_page.png (entire page)")
        print("   - bfo_viewport.png (visible area)")

        await browser.close()


if __name__ == "__main__":
    import os
    os.makedirs("data/screenshots", exist_ok=True)
    asyncio.run(take_screenshot())

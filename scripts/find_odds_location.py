#!/usr/bin/env python3
"""Find where the odds values actually live in the DOM."""

import asyncio
from playwright.async_api import async_playwright


async def find_odds():
    """Find the exact location of odds in the DOM."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto("https://www.bestfightodds.com/events/ufc-vegas-110-3913")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(8000)

        # Search for TD elements containing odds-like text
        result = await page.evaluate("""
            () => {
                const allTds = document.querySelectorAll('td');
                const oddsElements = [];

                for (let i = 0; i < Math.min(allTds.length, 100); i++) {
                    const td = allTds[i];
                    const text = td.textContent.trim();

                    // Look for odds-like patterns (+/- followed by numbers)
                    if (/[+-]\\d+/.test(text)) {
                        // Find the closest matchup ID
                        let currentElement = td;
                        let matchupId = null;
                        let depth = 0;

                        while (currentElement && depth < 20) {
                            if (currentElement.id && currentElement.id.startsWith('mu-')) {
                                matchupId = currentElement.id;
                                break;
                            }
                            // Check siblings
                            let sibling = currentElement.previousElementSibling;
                            while (sibling && depth < 20) {
                                if (sibling.id && sibling.id.startsWith('mu-')) {
                                    matchupId = sibling.id;
                                    break;
                                }
                                sibling = sibling.previousElementSibling;
                                depth++;
                            }
                            if (matchupId) break;

                            currentElement = currentElement.parentElement;
                            depth++;
                        }

                        oddsElements.push({
                            text: text,
                            html: td.outerHTML.substring(0, 300),
                            parent_tag: td.parentElement ? td.parentElement.tagName : 'NO PARENT',
                            parent_id: td.parentElement ? td.parentElement.id : '',
                            closest_matchup_id: matchupId,
                            td_index_in_row: Array.from(td.parentElement.children).indexOf(td)
                        });

                        if (oddsElements.length >= 20) break;  // Get first 20
                    }
                }

                return {
                    total_tds: allTds.length,
                    odds_found: oddsElements.length,
                    samples: oddsElements
                };
            }
        """)

        print("🔍 ODDS LOCATION ANALYSIS:")
        print("=" * 70)
        import json
        print(json.dumps(result, indent=2))

        await browser.close()


if __name__ == "__main__":
    asyncio.run(find_odds())

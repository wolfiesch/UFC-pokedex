#!/usr/bin/env python3
"""Debug script to understand the exact HTML structure of odds table."""

import asyncio
from playwright.async_api import async_playwright


async def debug_structure():
    """Debug the table structure to understand how odds are organized."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto("https://www.bestfightodds.com/events/ufc-vegas-110-3913")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(8000)

        # Get detailed information about the table structure
        result = await page.evaluate("""
            () => {
                const matchupRow = document.querySelector('#mu-40336');
                if (!matchupRow) return {error: 'Matchup not found'};

                const table = matchupRow.closest('table');
                const debug = {
                    matchup_row_html: matchupRow.outerHTML.substring(0, 500),
                    matchup_row_tag: matchupRow.tagName,
                    matchup_row_children: matchupRow.children.length,
                    table_tag: table ? table.tagName : 'NO TABLE',
                };

                // Get all children of matchup row
                const children = [];
                for (let child of matchupRow.children) {
                    children.push({
                        tag: child.tagName,
                        text: child.textContent.trim().substring(0, 100),
                        html: child.outerHTML.substring(0, 200)
                    });
                }
                debug.matchup_row_children_details = children;

                // Check next sibling
                const nextRow = matchupRow.nextElementSibling;
                if (nextRow) {
                    debug.next_row_html = nextRow.outerHTML.substring(0, 500);
                    debug.next_row_tag = nextRow.tagName;
                    debug.next_row_has_td = nextRow.querySelectorAll('td').length;
                }

                // Check if there are any TD elements at all near this matchup
                const allRows = table.querySelectorAll('tr');
                let found_odds = false;
                for (let i = 0; i < allRows.length && i < 50; i++) {
                    const row = allRows[i];
                    const tds = row.querySelectorAll('td');
                    if (tds.length > 0) {
                        for (let td of tds) {
                            const text = td.textContent.trim();
                            if (text.includes('+') || text.includes('-')) {
                                found_odds = true;
                                debug.sample_odds_row = {
                                    index: i,
                                    html: row.outerHTML.substring(0, 500),
                                    td_count: tds.length,
                                    first_td_text: tds[0] ? tds[0].textContent.trim() : ''
                                };
                                break;
                            }
                        }
                        if (found_odds) break;
                    }
                }

                // Get thead structure
                const thead = table.querySelector('thead');
                if (thead) {
                    const headerRow = thead.querySelector('tr');
                    if (headerRow) {
                        const headers = [];
                        for (let th of headerRow.children) {
                            headers.push({
                                tag: th.tagName,
                                text: th.textContent.trim().substring(0, 50),
                                html: th.outerHTML.substring(0, 150)
                            });
                        }
                        debug.table_headers = headers;
                    }
                }

                return debug;
            }
        """)

        print("🔍 DEBUG INFORMATION:")
        print("=" * 70)
        import json
        print(json.dumps(result, indent=2))

        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_structure())

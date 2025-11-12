#!/usr/bin/env python3
"""
Investigate if Best Fight Odds has historical line movement data.
Looking for charts, graphs, or historical odds tracking.
"""

import asyncio
from playwright.async_api import async_playwright


async def investigate_line_movement():
    """Check for line movement data in the page."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("📱 Loading UFC Vegas 110...")
        await page.goto("https://www.bestfightodds.com/events/ufc-vegas-110-3913")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(8000)

        print("\n🔍 Looking for line movement features...")

        # Look for chart/graph elements
        result = await page.evaluate("""
            () => {
                const debug = {
                    charts: [],
                    canvas_elements: document.querySelectorAll('canvas').length,
                    svg_elements: document.querySelectorAll('svg').length,
                    chart_divs: [],
                    highcharts: typeof Highcharts !== 'undefined',
                    chartjs: typeof Chart !== 'undefined',
                    d3: typeof d3 !== 'undefined'
                };

                // Look for chart containers
                const chartContainers = document.querySelectorAll('[id*="chart"], [class*="chart"], [id*="graph"], [class*="graph"]');
                chartContainers.forEach(elem => {
                    debug.chart_divs.push({
                        id: elem.id,
                        class: elem.className,
                        tag: elem.tagName
                    });
                });

                // Look for CreateMIChart or similar functions
                const scripts = document.querySelectorAll('script');
                let foundCreateMI = false;
                scripts.forEach(script => {
                    const content = script.textContent || script.innerText || '';
                    if (content.includes('CreateMIChart') || content.includes('CreateChart')) {
                        foundCreateMI = true;
                        debug.createMIChart_found = true;
                        debug.createMIChart_sample = content.substring(0, 500);
                    }
                });

                // Look for any data attributes that might contain historical data
                const dataElements = document.querySelectorAll('[data-chart], [data-graph], [data-odds-history]');
                debug.data_elements = dataElements.length;

                // Check for onclick handlers that might load charts
                const clickableOdds = document.querySelectorAll('td[onclick], span[onclick]');
                if (clickableOdds.length > 0) {
                    debug.clickable_odds = clickableOdds.length;
                    debug.first_onclick = clickableOdds[0].getAttribute('onclick');
                }

                return debug;
            }
        """)

        print("\n📊 INVESTIGATION RESULTS:")
        import json
        print(json.dumps(result, indent=2))

        # Try clicking on an odds cell to see if it opens a chart
        print("\n🖱️  Trying to click on an odds cell...")
        try:
            # Click on the first odds cell
            await page.click('td.but-sg:first-of-type', timeout=5000)
            await page.wait_for_timeout(2000)

            # Check if any modal or chart appeared
            modal_check = await page.evaluate("""
                () => {
                    const modals = document.querySelectorAll('[class*="modal"], [class*="popup"], [class*="dialog"]');
                    return {
                        modals_found: modals.length,
                        visible_elements: Array.from(modals).filter(m =>
                            m.offsetWidth > 0 && m.offsetHeight > 0
                        ).length
                    };
                }
            """)
            print(f"   Modals after click: {modal_check}")

            # Take a screenshot
            await page.screenshot(path="data/screenshots/after_odds_click.png")
            print("   Screenshot saved: data/screenshots/after_odds_click.png")

        except Exception as e:
            print(f"   Click failed: {e}")

        await browser.close()


if __name__ == "__main__":
    import os
    os.makedirs("data/screenshots", exist_ok=True)
    asyncio.run(investigate_line_movement())

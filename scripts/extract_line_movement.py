#!/usr/bin/env python3
"""
Extract historical line movement data from Best Fight Odds.
Discovered: Clicking on odds cells opens Highcharts with historical data!
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def extract_line_movement():
    """Extract line movement data by clicking odds and capturing chart data."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("📱 Loading UFC Vegas 110...")
        await page.goto("https://www.bestfightodds.com/events/ufc-vegas-110-3913")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(8000)

        print("\n🖱️  Clicking on first odds cell to open line movement chart...")

        # Find the first odds cell with actual odds
        first_odds_cell = await page.query_selector('td.but-sg')
        if not first_odds_cell:
            print("❌ No odds cells found!")
            await browser.close()
            return

        # Click to open the chart
        await first_odds_cell.click()
        await page.wait_for_timeout(3000)  # Wait for chart to load

        print("📊 Extracting chart data...")

        # Extract Highcharts data
        chart_data = await page.evaluate("""
            () => {
                // Highcharts stores chart data in the chart object
                const chartWindow = document.querySelector('#chart-window');
                const chartArea = document.querySelector('#chart-area');

                if (!chartWindow || !chartArea) {
                    return {error: 'Chart window not found'};
                }

                // Try to find Highcharts instance
                if (typeof Highcharts !== 'undefined' && Highcharts.charts) {
                    const charts = Highcharts.charts.filter(c => c !== undefined);
                    if (charts.length > 0) {
                        const chart = charts[0];
                        const data = {
                            chart_type: chart.options.chart.type,
                            title: chart.options.title.text,
                            series: [],
                            xAxis: {
                                type: chart.options.xAxis[0].type,
                                categories: chart.options.xAxis[0].categories
                            }
                        };

                        // Extract all series (one per bookmaker)
                        chart.series.forEach(series => {
                            const seriesData = {
                                name: series.name,
                                type: series.type,
                                visible: series.visible,
                                data: series.data.map(point => ({
                                    x: point.x,
                                    y: point.y,
                                    // Highcharts stores timestamp in x for datetime axis
                                    timestamp: point.category || point.x,
                                    value: point.y
                                }))
                            };
                            data.series.push(seriesData);
                        });

                        return data;
                    }
                }

                // Fallback: check if chart data is in DOM
                const chartHeader = document.querySelector('#chart-header');
                return {
                    error: 'Highcharts not accessible',
                    chart_header: chartHeader ? chartHeader.textContent : 'N/A',
                    chart_window_visible: chartWindow.offsetWidth > 0
                };
            }
        """)

        print("\n📈 LINE MOVEMENT DATA:")
        print(json.dumps(chart_data, indent=2))

        # Save to file
        with open('data/raw/line_movement_sample.json', 'w') as f:
            json.dump(chart_data, f, indent=2)
        print("\n💾 Saved to: data/raw/line_movement_sample.json")

        # Take screenshot of the chart
        await page.screenshot(path="data/screenshots/line_movement_chart.png")
        print("📸 Screenshot saved: data/screenshots/line_movement_chart.png")

        # Try to close the chart and click on another odds cell
        print("\n🔄 Trying to extract more odds...")
        try:
            # Close chart (look for close button)
            close_button = await page.query_selector('#chart-window .close, .popup-close, button.close')
            if close_button:
                await close_button.click()
                await page.wait_for_timeout(1000)
        except:
            pass

        await browser.close()


if __name__ == "__main__":
    import os
    os.makedirs("data/screenshots", exist_ok=True)
    os.makedirs("data/raw", exist_ok=True)
    asyncio.run(extract_line_movement())

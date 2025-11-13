from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import scrapy
from scrapy_playwright.page import PageMethod


class BestFightOddsFighterMeanOddsSpider(scrapy.Spider):
    """
    Spider to extract mean odds history from fighter pages on Best Fight Odds.

    This spider loads individual fighter pages and extracts the mean/average odds
    line charts for each of their fights. Much more efficient than event-based scraping.

    Usage:
        # Single fighter for testing
        scrapy crawl bestfightodds_fighter_mean_odds \
            -a fighter_urls="https://www.bestfightodds.com/fighters/Jack-Della-Maddalena-7492" \
            -o data/raw/bfo_fighter_mean_odds_test.jsonl

        # Multiple fighters from mapping file
        scrapy crawl bestfightodds_fighter_mean_odds \
            -a mapping_file="data/processed/bfo_fighter_url_mapping_corrected.jsonl" \
            -o data/raw/bfo_fighter_mean_odds.jsonl

        # Limit number of fighters (for testing)
        scrapy crawl bestfightodds_fighter_mean_odds \
            -a mapping_file="data/processed/bfo_fighter_url_mapping_corrected.jsonl" \
            -a max_fighters=10 \
            -o data/raw/bfo_fighter_mean_odds_test.jsonl
    """

    name = "bestfightodds_fighter_mean_odds"
    allowed_domains = ["bestfightodds.com"]

    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,  # Optimized from 4.0
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2.0,  # Optimized from 3.0
        "AUTOTHROTTLE_MAX_DELAY": 8.0,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "HTTPCACHE_ENABLED": False,  # Disable cache for playwright
        "ITEM_PIPELINES": {},
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
    }

    def start_requests(self):
        """Collect fighter URLs and start scraping."""
        urls = []

        # Option 1: Direct fighter URLs
        fighter_urls = getattr(self, "fighter_urls", None)
        if fighter_urls:
            urls.extend([url.strip() for url in fighter_urls.split(",") if url.strip()])

        # Option 2: Load from mapping file
        mapping_file = getattr(self, "mapping_file", None)
        if mapping_file:
            urls.extend(self._load_urls_from_mapping(mapping_file))

        if not urls:
            self.logger.error("No fighter URLs provided")
            return

        # Limit number of fighters if specified (for testing)
        max_fighters = int(getattr(self, "max_fighters", len(urls)))
        if max_fighters < len(urls):
            urls = urls[:max_fighters]
            self.logger.info(f"Limiting to {max_fighters} fighters")

        self.logger.info(f"Starting scrape for {len(urls)} fighters")

        for url in urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                dont_filter=True,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle", timeout=15000),
                        PageMethod("wait_for_timeout", 2000),
                    ],
                },
                errback=self.errback_close_page,
            )

    async def parse(self, response: scrapy.http.Response):
        """Parse fighter page and extract mean odds for each fight."""
        page = response.meta["playwright_page"]

        try:
            # Get fighter info from the page
            fighter_name = await page.locator("h1").text_content()
            fighter_url = response.url

            # Extract fighter ID from URL (e.g., Jack-Della-Maddalena-7492 -> 7492)
            fighter_id = fighter_url.rstrip("/").split("-")[-1]

            self.logger.info(f"Processing fighter: {fighter_name} (ID: {fighter_id})")

            # Wait for table to be fully loaded - try different selectors
            table_found = False
            for selector in ["table tr", "table tbody tr", ".table-wrapper tr"]:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    self.logger.info(f"Table found with selector: {selector}")
                    table_found = True
                    break
                except:
                    continue

            if not table_found:
                self.logger.error("Could not find table on page")
                return

            # Wait a bit for images to load
            await page.wait_for_timeout(2000)

            # Get all table rows from tbody (skip header)
            all_rows = await page.query_selector_all("table tbody tr")
            self.logger.info(f"Found {len(all_rows)} total tbody rows")

            # Check if ANY images exist on the page
            all_images = await page.query_selector_all("img")
            self.logger.info(f"Found {len(all_images)} total images on page")

            # Look for "main-row" class rows (these are fighter rows with chart data)
            main_rows = await page.query_selector_all("table tbody tr.main-row")
            self.logger.info(f"Found {len(main_rows)} main-row entries")

            # Filter for rows where this fighter is listed
            fight_rows = []
            for row in main_rows:
                # First column is <th class="oppcell"> containing fighter name
                th_cell = await row.query_selector("th.oppcell a")
                if not th_cell:
                    continue

                row_fighter_name = await th_cell.text_content()
                if row_fighter_name and row_fighter_name.strip() == fighter_name.strip():
                    fight_rows.append(row)

            self.logger.info(f"Found {len(fight_rows)} rows for fighter {fighter_name}")

            fights_processed = 0

            for idx, row in enumerate(fight_rows):
                self.logger.info(f"Processing row {idx + 1}/{len(fight_rows)}")

                try:
                    # Get opponent from next row (next sibling)
                    next_row = await row.evaluate_handle("el => el.nextElementSibling")
                    next_row_element = next_row.as_element()
                    if not next_row_element:
                        self.logger.warning(f"  No next row found - skipping")
                        continue

                    # Opponent is in <th class="oppcell"> of next row
                    opponent_cell = await next_row_element.query_selector("th.oppcell a")
                    opponent_name = await opponent_cell.text_content() if opponent_cell else None

                    if not opponent_name:
                        self.logger.warning(f"  No opponent name found - skipping")
                        continue

                    self.logger.info(f"  Fight vs {opponent_name}")

                    # Get event info from the row before this fighter row (event-header row)
                    prev_row = await row.evaluate_handle("el => el.previousElementSibling")
                    prev_row_element = prev_row.as_element()
                    event_name = None
                    event_url = None
                    if prev_row_element:
                        # Check if it's an event-header row
                        class_name = await prev_row_element.get_attribute("class")
                        if "event-header" in (class_name or ""):
                            event_link = await prev_row_element.query_selector("a")
                            event_name = await event_link.text_content() if event_link else None
                            event_url = (
                                await event_link.get_attribute("href") if event_link else None
                            )

                    # Extract odds data from td cells
                    td_cells = await row.query_selector_all("td")

                    # Based on the HTML structure: opening, closing range start, ..., closing range end, chart cell
                    opening_odds = None
                    closing_range_start = None
                    closing_range_end = None

                    if len(td_cells) >= 4:
                        opening_odds = await td_cells[0].text_content()
                        closing_range_start = await td_cells[1].text_content()
                        # td_cells[2] is the "..." dash
                        closing_range_end = await td_cells[3].text_content()

                    # Find the chart cell with data-li attribute
                    chart_cell = await row.query_selector("td.chart-cell[data-li]")
                    if not chart_cell:
                        self.logger.warning(
                            f"  No chart-cell with data-li found for {opponent_name} - skipping"
                        )
                        continue

                    # Get the data-li attribute to identify this chart
                    data_li = await chart_cell.get_attribute("data-li")
                    self.logger.info(f"  Found chart-cell with data-li={data_li}")

                    # Scroll to the element to ensure it's visible
                    await chart_cell.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)

                    # Try clicking the chart cell - this should open a modal with the full time-series chart
                    # Use force=True in case there are overlays
                    try:
                        await chart_cell.click(timeout=5000, force=True)
                        self.logger.info(f"  Clicked chart cell")
                        await page.wait_for_timeout(
                            2000
                        )  # Wait for modal to open and chart to render
                    except Exception as e:
                        self.logger.error(f"  Failed to click chart cell: {e}")
                        continue

                    # Extract mean odds data from the modal's Highcharts
                    mean_odds_data = await self._extract_mean_odds_chart(page)

                    if mean_odds_data:
                        self.logger.info(
                            f"  Extracted chart data: {mean_odds_data.get('error', 'success')}"
                        )
                        if "debug" in mean_odds_data:
                            self.logger.info(f"  Debug info: {mean_odds_data['debug']}")
                        if "series" in mean_odds_data and mean_odds_data["series"]:
                            self.logger.info(
                                f"  Got {len(mean_odds_data['series'][0].get('data', []))} data points"
                            )

                    # Close the modal
                    await self._close_chart_modal(page)
                    await page.wait_for_timeout(500)

                    fights_processed += 1

                    # Yield the data
                    result = {
                        "fighter_id": fighter_id,
                        "fighter_name": fighter_name.strip() if fighter_name else None,
                        "fighter_url": fighter_url,
                        "opponent_name": opponent_name.strip() if opponent_name else None,
                        "event_name": event_name.strip() if event_name else None,
                        "event_url": response.urljoin(event_url) if event_url else None,
                        "opening_odds": opening_odds.strip() if opening_odds else None,
                        "closing_range_start": closing_range_start.strip()
                        if closing_range_start
                        else None,
                        "closing_range_end": closing_range_end.strip()
                        if closing_range_end
                        else None,
                        "scraped_at": datetime.utcnow().isoformat(),
                    }

                    # Add mean odds time-series data if available
                    if (
                        mean_odds_data
                        and "series" in mean_odds_data
                        and len(mean_odds_data["series"]) > 0
                    ):
                        # Extract data from first series (mean odds)
                        series_data = mean_odds_data["series"][0]
                        result["mean_odds_history"] = series_data.get("data", [])
                        result["num_odds_points"] = len(series_data.get("data", []))
                        result["series_name"] = series_data.get("name")
                        result["chart_title"] = mean_odds_data.get("title")
                    else:
                        result["mean_odds_history"] = []
                        result["num_odds_points"] = 0
                        if mean_odds_data and "error" in mean_odds_data:
                            result["extraction_error"] = mean_odds_data["error"]

                    yield result

                except Exception as e:
                    self.logger.error(f"  Error processing fight: {e}")
                    import traceback

                    self.logger.error(traceback.format_exc())
                    continue

            self.logger.info(f"Completed {fighter_name}: processed {fights_processed} fights")

        finally:
            await page.close()

    async def _extract_mean_odds_chart(self, page) -> dict:
        """
        Extract mean odds data from the Highcharts line chart modal.

        The mean odds chart is a line chart with:
        - datetime x-axis (timestamps)
        - odds values on y-axis
        - single series showing the mean/average across all bookmakers
        """
        try:
            chart_data = await page.evaluate("""
                () => {
                    if (typeof Highcharts === 'undefined' || !Highcharts.charts) {
                        return {error: 'Highcharts not found'};
                    }

                    const allCharts = Highcharts.charts.filter(c => c !== undefined);
                    if (allCharts.length === 0) {
                        return {error: 'No charts found'};
                    }

                    // Find the line chart with datetime xAxis (the mean odds chart)
                    const lineChart = allCharts.find(c =>
                        c.options.chart.type === 'line' &&
                        c.options.xAxis &&
                        c.options.xAxis[0] &&
                        c.options.xAxis[0].type === 'datetime'
                    );

                    if (!lineChart) {
                        return {
                            error: 'No datetime line chart found',
                            debug: {
                                total_charts: allCharts.length,
                                chart_types: allCharts.map(c => ({
                                    type: c.options.chart.type,
                                    xAxisType: c.options.xAxis && c.options.xAxis[0] ? c.options.xAxis[0].type : null
                                }))
                            }
                        };
                    }

                    const result = {
                        title: lineChart.options.title ? lineChart.options.title.text : null,
                        chart_type: lineChart.options.chart.type,
                        xAxis_type: lineChart.options.xAxis[0].type,
                        series: []
                    };

                    // Extract the mean odds series (should be just one line)
                    lineChart.series.forEach(series => {
                        if (!series.visible) return;  // Skip hidden series

                        const seriesData = {
                            name: series.name,
                            data: []
                        };

                        // Extract data points (timestamp, odds value)
                        series.data.forEach(point => {
                            seriesData.data.push({
                                timestamp_ms: point.x,  // Unix timestamp in milliseconds
                                timestamp: new Date(point.x).toISOString(),  // ISO format
                                odds: point.y
                            });
                        });

                        result.series.push(seriesData);
                    });

                    return result;
                }
            """)

            return chart_data

        except Exception as e:
            self.logger.error(f"Error extracting Highcharts data: {e}")
            return {"error": str(e)}

    async def _close_chart_modal(self, page):
        """Close the chart modal window."""
        try:
            # Try multiple selectors for close button
            close_selectors = [
                "a:has-text('✕')",
                ".close",
                "button.close",
                "[aria-label='Close']",
            ]

            for selector in close_selectors:
                try:
                    close_btn = await page.query_selector(selector)
                    if close_btn:
                        await close_btn.click()
                        await page.wait_for_timeout(500)
                        return
                except:
                    continue

            # If no close button found, try pressing Escape
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)

        except Exception as e:
            self.logger.warning(f"Could not close chart modal: {e}")

    async def errback_close_page(self, failure):
        """Close page on error."""
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error(f"Request failed: {failure.request.url}")

    def _load_urls_from_mapping(self, file_path: str) -> list[str]:
        """Load fighter URLs from corrected mapping file."""
        path = Path(file_path)
        if not path.exists():
            self.logger.error(f"Mapping file not found: {file_path}")
            return []

        urls = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if bfo_url := data.get("bfo_url"):
                        urls.append(bfo_url)
                except json.JSONDecodeError:
                    continue

        self.logger.info(f"Loaded {len(urls)} fighter URLs from {file_path}")
        return urls

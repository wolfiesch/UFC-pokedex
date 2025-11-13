from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import scrapy


class BestFightOddsLineMovementSpider(scrapy.Spider):
    """
    Spider to extract historical line movement data from Best Fight Odds.

    This spider clicks on odds cells to open Highcharts modals and extracts
    the complete line movement history (opening to closing with timestamps).

    Usage:
        # Single event with line movement history
        scrapy crawl bestfightodds_line_movement \
            -a event_urls="https://www.bestfightodds.com/events/ufc-vegas-110-3913" \
            -o data/raw/bfo_line_movement.jsonl

        # Limit number of clicks per event (for testing)
        scrapy crawl bestfightodds_line_movement \
            -a event_urls="https://www.bestfightodds.com/events/ufc-vegas-110-3913" \
            -a max_clicks=5 \
            -o data/raw/bfo_line_movement_test.jsonl
    """

    name = "bestfightodds_line_movement"
    allowed_domains = ["bestfightodds.com"]

    custom_settings = {
        "DOWNLOAD_DELAY": 4.0,  # Slower for clicking interactions
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 3.0,
        "AUTOTHROTTLE_MAX_DELAY": 10.0,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "ITEM_PIPELINES": {},
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
    }

    def start_requests(self):
        """Collect event URLs and start scraping."""
        urls = []

        event_urls = getattr(self, "event_urls", None)
        if event_urls:
            urls.extend([url.strip() for url in event_urls.split(",") if url.strip()])

        input_file = getattr(self, "input_file", None)
        if input_file:
            urls.extend(self._load_urls_from_file(input_file))

        if not urls:
            default_file = Path("data/raw/bfo_events_archive.jsonl")
            if default_file.exists():
                self.logger.info(f"Loading events from: {default_file}")
                urls.extend(self._load_urls_from_file(str(default_file)))

        if not urls:
            self.logger.error("No event URLs provided")
            return

        for url in urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                dont_filter=True,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        ("wait_for_load_state", "networkidle", {"timeout": 15000}),
                        ("wait_for_timeout", 8000),
                    ],
                },
                errback=self.errback_close_page,
            )

    async def parse(self, response: scrapy.http.Response):
        """Parse event page and extract line movement for each odds cell."""
        page = response.meta["playwright_page"]

        try:
            event_title = response.css("div.table-header h1::text").get()
            event_date = response.css("span.table-header-date::text").get()
            event_url = response.url

            event_id_match = re.search(r"/events/(.+-(\d+))$", event_url)
            event_id = event_id_match.group(1) if event_id_match else None

            # Get max clicks limit (for testing)
            max_clicks = int(getattr(self, "max_clicks", 999))
            clicks_done = 0

            # Get all matchup rows
            matchup_rows = response.css('tr[id^="mu-"]')

            for matchup_row in matchup_rows:
                if clicks_done >= max_clicks:
                    self.logger.info(f"Reached max_clicks limit ({max_clicks})")
                    break

                matchup_id = matchup_row.css("::attr(id)").get()
                if matchup_id:
                    matchup_id = matchup_id.replace("mu-", "")

                # Get fighter names
                fighter_1_link = matchup_row.css("th a")
                fighter_1_name = fighter_1_link.css("::text").get()
                fighter_1_url = fighter_1_link.css("::attr(href)").get()

                fighter_2_row = matchup_row.xpath("./following-sibling::tr[1]")
                fighter_2_link = fighter_2_row.css("th a")
                fighter_2_name = fighter_2_link.css("::text").get()
                fighter_2_url = fighter_2_link.css("::attr(href)").get()

                if not fighter_1_name or not fighter_2_name:
                    continue

                self.logger.info(f"Processing: {fighter_1_name} vs {fighter_2_name}")

                # Find all odds cells for this matchup using data-li attribute
                odds_cells = await page.query_selector_all(f'td[data-li*=",{matchup_id}"]')

                self.logger.info(f"Found {len(odds_cells)} odds cells for matchup {matchup_id}")

                # Click each odds cell and extract line movement
                for i, cell in enumerate(odds_cells):
                    if clicks_done >= max_clicks:
                        break

                    try:
                        # Get the data-li attribute to identify the bookmaker
                        data_li = await cell.get_attribute("data-li")
                        if not data_li:
                            continue

                        # Parse [bookmaker_id, fighter_num, matchup_id, ...]
                        data_li_parsed = json.loads(data_li)
                        bookmaker_id = data_li_parsed[0] if len(data_li_parsed) > 0 else None
                        fighter_num = data_li_parsed[1] if len(data_li_parsed) > 1 else None

                        self.logger.info(
                            f"  Clicking cell {i + 1}/{len(odds_cells)}: "
                            f"bookmaker={bookmaker_id}, fighter={fighter_num}"
                        )

                        # Scroll cell into view and ensure visibility
                        try:
                            # Check if element is visible first (fast check)
                            is_visible = await cell.is_visible()
                            if not is_visible:
                                # Try to scroll into view with short timeout
                                try:
                                    await cell.scroll_into_view_if_needed(
                                        timeout=3000
                                    )  # 3s timeout
                                    await page.wait_for_timeout(200)  # Let scroll complete
                                    is_visible = await cell.is_visible()
                                except:
                                    pass  # Scroll failed, check visibility below

                            if not is_visible:
                                self.logger.warning(f"  Cell {i + 1} not visible, skipping")
                                continue

                        except Exception as scroll_err:
                            self.logger.warning(
                                f"  Error checking visibility for cell {i + 1}, skipping"
                            )
                            continue

                        # Click the cell to open chart (with shorter timeout)
                        try:
                            await cell.click(timeout=10000)  # 10s timeout instead of 30s
                        except Exception as click_err:
                            self.logger.warning(
                                f"  Click timeout on cell {i + 1}: {click_err}, skipping"
                            )
                            continue

                        await page.wait_for_timeout(2000)  # Wait for chart to load

                        # Extract line movement data from Highcharts
                        line_data = await self._extract_highcharts_data(page)

                        # Close the chart modal
                        await self._close_chart_modal(page)
                        await page.wait_for_timeout(500)

                        clicks_done += 1

                        # Yield the data
                        yield {
                            "event_id": event_id,
                            "event_title": event_title.strip() if event_title else None,
                            "event_date": event_date.strip() if event_date else None,
                            "event_url": event_url,
                            "matchup_id": matchup_id,
                            "fighter_1": {
                                "name": fighter_1_name.strip() if fighter_1_name else None,
                                "url": response.urljoin(fighter_1_url) if fighter_1_url else None,
                            },
                            "fighter_2": {
                                "name": fighter_2_name.strip() if fighter_2_name else None,
                                "url": response.urljoin(fighter_2_url) if fighter_2_url else None,
                            },
                            "bookmaker_id": bookmaker_id,
                            "fighter_number": fighter_num,
                            "line_movement": line_data,
                            "scraped_at": datetime.utcnow().isoformat(),
                        }

                    except Exception as e:
                        self.logger.error(f"Error clicking cell {i}: {e}")
                        # Try to close any open modals
                        await self._close_chart_modal(page)
                        continue

        finally:
            await page.close()

    async def _extract_highcharts_data(self, page) -> dict:
        """Extract line movement data from Highcharts modal.

        Note: There are multiple charts on the page:
        - Chart 0: Comparison bar chart (wrong)
        - Chart 1: Expected outcome chart (wrong)
        - Chart 2+: Line chart with datetime axis (correct!)

        We need to find the line chart with datetime xAxis.
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

                    // Find the line chart with datetime xAxis (the correct one!)
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

                    // Extract all visible series (typically one per bookmaker)
                    lineChart.series.forEach(series => {
                        if (!series.visible) return;  // Skip hidden series

                        const seriesData = {
                            name: series.name,
                            data: []
                        };

                        // Extract data points (timestamp, odds value)
                        series.data.forEach(point => {
                            seriesData.data.push({
                                timestamp: point.category || point.x,
                                value: point.y,
                                // For datetime axis, x is timestamp in milliseconds
                                timestamp_ms: typeof point.x === 'number' ? point.x : null
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
                "#chart-window .close",
                "#chart-window button.close",
                ".popup-close",
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

    def _load_urls_from_file(self, file_path: str) -> list[str]:
        """Load event URLs from JSONL file."""
        path = Path(file_path)
        if not path.exists():
            return []

        urls = []
        organization_filter = getattr(self, "organization", None)

        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if organization_filter:
                        if data.get("organization", "").upper() != organization_filter.upper():
                            continue
                    event_url = data.get("event_url")
                    if event_url:
                        urls.append(event_url)
                except json.JSONDecodeError:
                    continue

        self.logger.info(f"Loaded {len(urls)} event URLs from {file_path}")
        return urls

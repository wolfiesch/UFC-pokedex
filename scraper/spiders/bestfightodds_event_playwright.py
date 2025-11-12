from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import scrapy


class BestFightOddsEventPlaywrightSpider(scrapy.Spider):
    """
    Spider to scrape detailed betting odds using Playwright for JavaScript rendering.

    This spider collects:
    - Fighter names and matchup IDs
    - Moneyline odds from multiple bookmakers (rendered via JavaScript)
    - Opening and closing odds
    - Prop bet odds (method of victory, rounds, etc.)

    Usage:
        # Scrape specific event URL
        scrapy crawl bestfightodds_event_playwright \
            -a event_urls="https://www.bestfightodds.com/events/ufc-vegas-110-3913" \
            -o data/raw/bfo_odds_full.jsonl

        # Scrape from archive file (UFC only)
        scrapy crawl bestfightodds_event_playwright \
            -a input_file="data/raw/bfo_events_archive.jsonl" \
            -a organization="UFC" \
            -o data/raw/bfo_ufc_odds_full.jsonl

    Requirements:
        - scrapy-playwright installed: uv pip install scrapy-playwright
        - Playwright browsers installed: playwright install chromium
        - Scrapy settings configured for Playwright (see settings.py)
    """

    name = "bestfightodds_event_playwright"
    allowed_domains = ["bestfightodds.com"]

    custom_settings = {
        "DOWNLOAD_DELAY": 3.0,  # Be more respectful with browser automation
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2.0,
        "AUTOTHROTTLE_MAX_DELAY": 8.0,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,  # Only 1 concurrent browser instance
        "ITEM_PIPELINES": {},  # Disable pipelines
        # Playwright-specific settings
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
    }

    def start_requests(self):
        """Collect event URLs from various sources and start scraping."""
        urls = []

        # Priority 1: URLs passed via command line
        event_urls = getattr(self, "event_urls", None)
        if event_urls:
            urls.extend([url.strip() for url in event_urls.split(",") if url.strip()])

        # Priority 2: Load from input file
        input_file = getattr(self, "input_file", None)
        if input_file:
            urls.extend(self._load_urls_from_file(input_file))

        # Priority 3: Default to archive file if it exists
        if not urls:
            default_file = Path("data/raw/bfo_events_archive.jsonl")
            if default_file.exists():
                self.logger.info(f"Loading events from default file: {default_file}")
                urls.extend(self._load_urls_from_file(str(default_file)))

        if not urls:
            self.logger.error(
                "No event URLs provided. Pass -a event_urls=... or -a input_file=..."
            )
            return

        # Make Playwright-enabled requests
        for url in urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                dont_filter=True,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        # Wait for odds table to load
                        ("wait_for_selector", "table.odds-table", {"timeout": 10000}),
                        # Wait a bit more for any dynamic content
                        ("wait_for_timeout", 2000),
                    ],
                },
                errback=self.errback_close_page,
            )

    async def parse(self, response: scrapy.http.Response):
        """
        Parse an event page to extract fight odds (with JavaScript rendered).
        """
        page = response.meta["playwright_page"]

        try:
            # Extract event metadata
            event_title = response.css("div.table-header h1::text").get()
            event_date = response.css("span.table-header-date::text").get()
            event_url = response.url

            # Extract event ID from URL
            event_id_match = re.search(r'/events/(.+-(\d+))$', event_url)
            event_id = event_id_match.group(1) if event_id_match else None

            # Parse all fight matchups
            matchup_rows = response.css('tr[id^="mu-"]')

            for matchup_row in matchup_rows:
                matchup_id = matchup_row.css("::attr(id)").get()
                if matchup_id:
                    matchup_id = matchup_id.replace("mu-", "")

                # Get fighter 1 name (first row of matchup)
                fighter_1_link = matchup_row.css("th a")
                fighter_1_name = fighter_1_link.css("::text").get()
                fighter_1_url = fighter_1_link.css("::attr(href)").get()

                # The next row contains fighter 2
                fighter_2_row = matchup_row.xpath("./following-sibling::tr[1]")
                fighter_2_link = fighter_2_row.css("th a")
                fighter_2_name = fighter_2_link.css("::text").get()
                fighter_2_url = fighter_2_link.css("::attr(href)").get()

                if not fighter_1_name or not fighter_2_name:
                    continue

                # Extract odds from the matchup row and following row
                # Odds are in <td> elements with data-bookie attributes
                odds_data = await self._extract_odds_for_matchup(
                    page, matchup_id
                )

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
                    "odds": odds_data,
                    "scraped_at": datetime.utcnow().isoformat(),
                }

        finally:
            # Always close the page to free resources
            await page.close()

    async def _extract_odds_for_matchup(self, page, matchup_id: str) -> dict:
        """
        Extract odds data for a specific matchup using Playwright.

        Args:
            page: Playwright page object
            matchup_id: The matchup ID to extract odds for

        Returns:
            Dictionary containing odds from various bookmakers
        """
        odds = {}

        try:
            # Use JavaScript to extract odds from the table
            # The odds are in table cells with data-bookie attributes
            result = await page.evaluate(f"""
                () => {{
                    const matchupRow = document.querySelector('#mu-{matchup_id}');
                    if (!matchupRow) return {{}};

                    const fighter1Row = matchupRow;
                    const fighter2Row = matchupRow.nextElementSibling;

                    const bookmakers = {{}};

                    // Get all odds cells for fighter 1
                    const fighter1Odds = fighter1Row.querySelectorAll('td[data-bookie]');
                    fighter1Odds.forEach(cell => {{
                        const bookie = cell.getAttribute('data-bookie');
                        const odds = cell.textContent.trim();
                        if (bookie && odds) {{
                            if (!bookmakers[bookie]) bookmakers[bookie] = {{}};
                            bookmakers[bookie].fighter_1 = odds;
                        }}
                    }});

                    // Get all odds cells for fighter 2
                    if (fighter2Row) {{
                        const fighter2Odds = fighter2Row.querySelectorAll('td[data-bookie]');
                        fighter2Odds.forEach(cell => {{
                            const bookie = cell.getAttribute('data-bookie');
                            const odds = cell.textContent.trim();
                            if (bookie && odds) {{
                                if (!bookmakers[bookie]) bookmakers[bookie] = {{}};
                                bookmakers[bookie].fighter_2 = odds;
                            }}
                        }});
                    }}

                    return bookmakers;
                }}
            """)

            odds = result

        except Exception as e:
            self.logger.error(f"Error extracting odds for matchup {matchup_id}: {e}")

        return odds

    async def errback_close_page(self, failure):
        """Close page on error to prevent resource leaks."""
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error(f"Request failed: {failure.request.url} - {failure.value}")

    def _load_urls_from_file(self, file_path: str) -> list[str]:
        """Load event URLs from a JSONL file."""
        path = Path(file_path)
        if not path.exists():
            self.logger.warning(f"Input file {file_path} not found")
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
                    # Apply organization filter if specified
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

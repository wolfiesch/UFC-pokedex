from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import scrapy


class BestFightOddsEventWorkingSpider(scrapy.Spider):
    """
    WORKING spider that successfully extracts betting odds using Playwright.

    This spider extracts odds by reading the text content of table cells
    after JavaScript rendering, which populates the odds values.

    Usage:
        scrapy crawl bestfightodds_event_working \
            -a event_urls="https://www.bestfightodds.com/events/ufc-vegas-110-3913" \
            -o data/raw/bfo_odds_working.jsonl
    """

    name = "bestfightodds_event_working"
    allowed_domains = ["bestfightodds.com"]

    custom_settings = {
        "DOWNLOAD_DELAY": 3.0,
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2.0,
        "AUTOTHROTTLE_MAX_DELAY": 8.0,
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
                self.logger.info(f"Loading events from default file: {default_file}")
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
                        ("wait_for_timeout", 8000),  # Critical: wait for odds to load
                    ],
                },
                errback=self.errback_close_page,
            )

    async def parse(self, response: scrapy.http.Response):
        """Parse event page and extract fight odds."""
        page = response.meta["playwright_page"]

        try:
            event_title = response.css("div.table-header h1::text").get()
            event_date = response.css("span.table-header-date::text").get()
            event_url = response.url

            event_id_match = re.search(r'/events/(.+-(\d+))$', event_url)
            event_id = event_id_match.group(1) if event_id_match else None

            # Get all matchup rows
            matchup_rows = response.css('tr[id^="mu-"]')

            for matchup_row in matchup_rows:
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

                # Extract odds using JavaScript evaluation
                odds_data = await self._extract_odds_from_table(page, matchup_id)

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
            await page.close()

    async def _extract_odds_from_table(self, page, matchup_id: str) -> dict:
        """
        Extract odds by reading table cell text content.

        The odds are in <td> elements within the table structure.
        We need to find the matchup row and extract all odds cells.
        """
        try:
            result = await page.evaluate(f"""
                () => {{
                    const matchupRow = document.querySelector('#mu-{matchup_id}');
                    if (!matchupRow) return {{}};

                    // Find the parent table
                    const table = matchupRow.closest('table');
                    if (!table) return {{}};

                    // Get all td elements in the first two rows (fighter 1 and fighter 2)
                    const fighter1Row = matchupRow;
                    const fighter2Row = matchupRow.nextElementSibling;

                    const odds = {{}};

                    // Extract odds from fighter 1 row
                    const fighter1Cells = fighter1Row.querySelectorAll('td');
                    const fighter1Odds = [];
                    fighter1Cells.forEach((cell, idx) => {{
                        const text = cell.textContent.trim();
                        if (text) {{
                            fighter1Odds.push({{
                                index: idx,
                                value: text,
                                html: cell.innerHTML.trim()
                            }});
                        }}
                    }});

                    // Extract odds from fighter 2 row
                    if (fighter2Row) {{
                        const fighter2Cells = fighter2Row.querySelectorAll('td');
                        const fighter2Odds = [];
                        fighter2Cells.forEach((cell, idx) => {{
                            const text = cell.textContent.trim();
                            if (text) {{
                                fighter2Odds.push({{
                                    index: idx,
                                    value: text,
                                    html: cell.innerHTML.trim()
                                }});
                            }}
                        }});
                        odds.fighter_2_odds = fighter2Odds;
                    }}

                    odds.fighter_1_odds = fighter1Odds;

                    // Try to extract bookmaker headers
                    const thead = table.querySelector('thead');
                    if (thead) {{
                        const headerCells = thead.querySelectorAll('th');
                        const bookmakers = [];
                        headerCells.forEach((cell, idx) => {{
                            const text = cell.textContent.trim();
                            if (text && idx > 0) {{  // Skip first column (fighter names)
                                bookmakers.push({{
                                    index: idx - 1,
                                    name: text
                                }});
                            }}
                        }});
                        odds.bookmakers = bookmakers;
                    }}

                    return odds;
                }}
            """)

            return result

        except Exception as e:
            self.logger.error(f"Error extracting odds for matchup {matchup_id}: {e}")
            return {}

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

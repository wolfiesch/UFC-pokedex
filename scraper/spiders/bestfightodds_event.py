from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import scrapy


class BestFightOddsEventSpider(scrapy.Spider):
    """
    Spider to scrape detailed betting odds for UFC events from Best Fight Odds.

    This spider collects:
    - Fighter names
    - Moneyline odds from multiple bookmakers
    - Opening and closing odds
    - Prop bet odds (method of victory, rounds, etc.)

    Usage:
        # Scrape specific event URLs
        scrapy crawl bestfightodds_event -a event_urls="https://www.bestfightodds.com/events/ufc-vegas-111-3917"

        # Scrape from archive file
        scrapy crawl bestfightodds_event -a input_file="data/raw/bfo_events_archive.jsonl"

        # Filter UFC events only
        scrapy crawl bestfightodds_event -a input_file="data/raw/bfo_events_archive.jsonl" -a organization="UFC"
    """

    name = "bestfightodds_event"
    allowed_domains = ["bestfightodds.com"]

    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,  # Be respectful
        "USER_AGENT": "UFC-Pokedex-Scraper/0.1 (+local)",
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1.5,
        "AUTOTHROTTLE_MAX_DELAY": 5.0,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "ITEM_PIPELINES": {},  # Disable pipelines for this spider
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

        # Make requests
        for url in urls:
            yield scrapy.Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response: scrapy.http.Response):
        """
        Parse an event page to extract fight odds.

        The page structure contains:
        - Event title and date in .table-header
        - Fighter matchups in table rows
        - Odds data in table cells (dynamically loaded via JavaScript)
        """
        # Extract event metadata
        event_title = response.css("div.table-header h1::text").get()
        event_date = response.css("span.table-header-date::text").get()
        event_url = response.url

        # Extract event ID from URL
        event_id_match = re.search(r'/events/(.+-(\d+))$', event_url)
        event_id = event_id_match.group(1) if event_id_match else None

        # Parse all fight matchups
        # The HTML structure has rows with id="mu-{matchup_id}"
        matchup_rows = response.css('tr[id^="mu-"]')

        for matchup_row in matchup_rows:
            matchup_id = matchup_row.css("::attr(id)").get()
            if matchup_id:
                matchup_id = matchup_id.replace("mu-", "")

            # Get fighter name (first row of matchup)
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

            # Note: The actual odds data is loaded via JavaScript, so we need to
            # either use Selenium/Playwright or find the API endpoint that loads the odds
            # For now, we'll yield the matchup metadata
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
                "odds": {},  # Will be populated by JavaScript scraper
                "scraped_at": datetime.utcnow().isoformat(),
            }

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

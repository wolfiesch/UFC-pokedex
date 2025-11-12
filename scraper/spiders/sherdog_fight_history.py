"""Spider to scrape complete fight histories from Sherdog profiles."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import scrapy

from scraper.config import settings
from scraper.utils.sherdog_fight_parser import parse_sherdog_fight_history

logger = logging.getLogger(__name__)


class SherdogFightHistorySpider(scrapy.Spider):
    """Scrape complete fight histories from Sherdog fighter pages.

    This spider loads a list of fighters (from FightMatrix or other sources),
    searches Sherdog for each fighter, and extracts their complete fight history.

    Input:
        data/processed/non_ufc_fightmatrix_fighters.json - Fighters to scrape
            Format: {"fighters": [{"name": "...", "profile_url": "...", ...}]}

    Output:
        data/processed/sherdog_fight_histories.jsonl - Fight records per line
            Format: {"fighter_name": "...", "sherdog_id": 123, "fights": [...]}
    """

    name = "sherdog_fight_history"
    allowed_domains = ["sherdog.com"]
    custom_settings = {
        "DOWNLOAD_DELAY": settings.delay_seconds,
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2.0,
        "AUTOTHROTTLE_MAX_DELAY": 10.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 2.0,
        "ITEM_PIPELINES": {
            "scraper.pipelines.storage.StoragePipeline": 200,
        },
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429],
    }

    def __init__(self, input_file: str | None = None, limit: int | None = None, *args, **kwargs):
        """Initialize spider.

        Args:
            input_file: Path to JSON file with fighter list (optional)
            limit: Maximum number of fighters to scrape (for testing)
        """
        super().__init__(*args, **kwargs)

        if input_file:
            self.input_file = Path(input_file)
        else:
            self.input_file = Path("data/processed/non_ufc_fightmatrix_fighters.json")

        self.limit = int(limit) if limit else None
        self.scraped_count = 0

    def start_requests(self):
        """Load fighters and initiate Sherdog profile requests."""
        if not self.input_file.exists():
            logger.error(f"Input file not found: {self.input_file}")
            logger.error("Please run: python scripts/extract_non_ufc_fightmatrix.py first")
            return

        with self.input_file.open() as f:
            data = json.load(f)

        fighters = data.get("fighters", [])
        if not fighters:
            logger.error("No fighters found in input file")
            return

        logger.info(f"Loaded {len(fighters)} fighters to scrape")
        if self.limit:
            fighters = fighters[:self.limit]
            logger.info(f"Limiting to first {self.limit} fighters")

        for fighter in fighters:
            # Build Sherdog search URL
            # FightMatrix profile URLs look like: /fighter-profile/Name/ID
            # We'll search Sherdog by name
            fighter_name = fighter.get("name")

            if not fighter_name:
                logger.warning(f"Skipping fighter with no name: {fighter}")
                continue

            # Try direct Sherdog URL if available from previous matches
            # Otherwise we'll need to search
            # For now, we'll use the search approach
            search_url = self._build_sherdog_search_url(fighter_name)

            yield scrapy.Request(
                search_url,
                callback=self.parse_search_results,
                meta={"fighter": fighter},
                dont_filter=True,
                errback=self.handle_error,
            )

    def _build_sherdog_search_url(self, fighter_name: str) -> str:
        """Build Sherdog search URL for a fighter.

        Args:
            fighter_name: Fighter's name

        Returns:
            Sherdog search URL
        """
        from urllib.parse import quote_plus
        search_term = quote_plus(fighter_name)
        return f"https://www.sherdog.com/stats/fightfinder?SearchTxt={search_term}"

    def parse_search_results(self, response: scrapy.http.Response):
        """Parse Sherdog search results and navigate to first match.

        Args:
            response: Scrapy response from Sherdog search page
        """
        fighter = response.meta["fighter"]
        fighter_name = fighter["name"]

        # Find fighter results in the search page
        result_rows = response.css("table.fightfinder_result tr")

        if not result_rows:
            # Try alternative selector
            result_rows = response.css("div.fighter_result")

        if not result_rows or len(result_rows) < 2:  # Need at least header + 1 result
            logger.warning(f"No search results found for {fighter_name}")
            return

        # Get first match (skip header row)
        first_result = result_rows[1]

        # Extract Sherdog profile URL
        fighter_link = first_result.css("a[href*='/fighter/']::attr(href)").get()

        if not fighter_link:
            logger.warning(f"No profile link found for {fighter_name}")
            return

        # Build full URL
        if not fighter_link.startswith("http"):
            fighter_link = f"https://www.sherdog.com{fighter_link}"

        # Extract Sherdog ID from URL
        sherdog_id = None
        parts = fighter_link.rstrip("/").split("-")
        if parts:
            try:
                sherdog_id = int(parts[-1])
            except ValueError:
                pass

        logger.info(f"Found Sherdog profile for {fighter_name}: {fighter_link}")

        # Navigate to fighter profile to get fight history
        yield scrapy.Request(
            fighter_link,
            callback=self.parse_fighter_profile,
            meta={
                "fighter": fighter,
                "sherdog_id": sherdog_id,
                "sherdog_url": fighter_link,
            },
            dont_filter=True,
            errback=self.handle_error,
        )

    def parse_fighter_profile(self, response: scrapy.http.Response):
        """Parse Sherdog fighter profile and extract fight history.

        Args:
            response: Scrapy response from Sherdog fighter page
        """
        fighter = response.meta["fighter"]
        sherdog_id = response.meta["sherdog_id"]
        sherdog_url = response.meta["sherdog_url"]
        fighter_name = fighter["name"]

        try:
            # Parse fight history using our utility
            fights = parse_sherdog_fight_history(response, sherdog_id)

            if not fights:
                logger.warning(f"No fights found for {fighter_name}")
                # Still yield the fighter record with empty fights list
                fights = []

            # Build output record
            output = {
                "item_type": "sherdog_fight_history",
                "fighter_name": fighter_name,
                "sherdog_id": sherdog_id,
                "sherdog_url": sherdog_url,
                "fightmatrix_profile_url": fighter.get("profile_url"),
                "division": fighter.get("division"),
                "rank": fighter.get("rank"),
                "total_fights": len(fights),
                "fights": fights,
            }

            # Calculate stats
            if fights:
                wins = sum(1 for f in fights if f["result"] == "Win")
                losses = sum(1 for f in fights if f["result"] == "Loss")
                draws = sum(1 for f in fights if f["result"] == "Draw")
                ncs = sum(1 for f in fights if f["result"] == "NC")

                output["record"] = {
                    "wins": wins,
                    "losses": losses,
                    "draws": draws,
                    "no_contests": ncs,
                    "record_string": f"{wins}-{losses}-{draws}" + (f" ({ncs} NC)" if ncs > 0 else ""),
                }

                # Identify promotions fought in
                promotions = {}
                for fight in fights:
                    promo = fight.get("promotion")
                    if promo:
                        promotions[promo] = promotions.get(promo, 0) + 1

                output["promotions"] = promotions

            logger.info(
                f"✅ Scraped {fighter_name}: {len(fights)} fights, "
                f"Record: {output.get('record', {}).get('record_string', 'N/A')}"
            )

            self.scraped_count += 1
            yield output

        except Exception as e:
            logger.error(f"Error parsing fight history for {fighter_name}: {e}")

    def handle_error(self, failure):
        """Handle request errors.

        Args:
            failure: Twisted Failure object
        """
        request = failure.request
        fighter = request.meta.get("fighter", {})
        fighter_name = fighter.get("name", "Unknown")

        logger.error(f"Request failed for {fighter_name}: {failure.value}")

    def closed(self, reason):
        """Called when spider closes.

        Args:
            reason: Reason for closing
        """
        logger.info(f"Spider closed: {reason}")
        logger.info(f"Total fighters scraped: {self.scraped_count}")

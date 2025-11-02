"""Spider to search Sherdog for UFC fighters and match them."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import scrapy

from scraper.config import settings
from scraper.utils.fuzzy_match import calculate_match_confidence

logger = logging.getLogger(__name__)


class SherdogSearchSpider(scrapy.Spider):
    """Search Sherdog for UFC fighters and calculate match confidence scores.

    This spider loads UFC fighter data from a JSON file, searches Sherdog for each
    fighter, and calculates confidence scores for potential matches using fuzzy matching.

    Input:
        data/active_fighters.json - List of UFC fighters to match
            Format: [{"id": "...", "name": "...", "division": "...", "record": "..."}]

    Output:
        data/processed/sherdog_matches.json - Matched fighters with confidence scores
            Format: {
                "ufc_id": {
                    "ufc_fighter": {...},
                    "matches": [{"sherdog_id": ..., "confidence": ..., ...}]
                }
            }
    """

    name = "sherdog_search"
    allowed_domains = ["sherdog.com"]
    custom_settings = {
        "DOWNLOAD_DELAY": settings.delay_seconds,
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2.0,
        "AUTOTHROTTLE_MAX_DELAY": 10.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 2.0,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fighters_file = Path("data/active_fighters.json")
        self.matches: dict[str, Any] = {}

    def start_requests(self):
        """Load fighters from JSON and initiate Sherdog searches."""
        if not self.fighters_file.exists():
            logger.error(f"Fighters file not found: {self.fighters_file}")
            logger.error("Please run: make export-active-fighters first")
            return

        with self.fighters_file.open() as f:
            fighters = json.load(f)

        logger.info(f"Loaded {len(fighters)} fighters to search on Sherdog")

        for fighter in fighters:
            # URL encode the fighter name for search
            search_term = quote_plus(fighter["name"])
            search_url = f"https://www.sherdog.com/stats/fightfinder?SearchTxt={search_term}"

            yield scrapy.Request(
                search_url,
                callback=self.parse_search_results,
                meta={"ufc_fighter": fighter},
                dont_filter=True,
            )

    def parse_search_results(self, response: scrapy.http.Response):
        """Parse Sherdog search results and calculate match confidence.

        Args:
            response: Scrapy response from Sherdog search page
        """
        ufc_fighter = response.meta["ufc_fighter"]
        ufc_id = ufc_fighter["id"]

        # Find fighter results in the search page
        # Sherdog search results are in a table with class "fightfinder_result"
        result_rows = response.css("table.fightfinder_result tr")

        if not result_rows:
            # Try alternative selector for newer Sherdog layout
            result_rows = response.css("div.fighter_result")

        matches = []

        for row in result_rows:
            # Extract fighter data from search result
            sherdog_data = self._extract_sherdog_data(row)

            if not sherdog_data:
                continue

            # Calculate confidence score
            confidence = calculate_match_confidence(ufc_fighter, sherdog_data)

            matches.append({
                "sherdog_id": sherdog_data.get("sherdog_id"),
                "sherdog_url": sherdog_data.get("url"),
                "name": sherdog_data.get("name"),
                "division": sherdog_data.get("division"),
                "record": sherdog_data.get("record"),
                "confidence": confidence,
            })

        # Sort matches by confidence (highest first)
        matches.sort(key=lambda x: x["confidence"], reverse=True)

        # Only keep top 3 matches
        top_matches = matches[:3]

        if top_matches:
            logger.info(
                f"Found {len(top_matches)} matches for {ufc_fighter['name']} "
                f"(best: {top_matches[0]['confidence']}%)"
            )
        else:
            logger.warning(f"No matches found for {ufc_fighter['name']}")

        # Yield the result
        yield {
            "ufc_id": ufc_id,
            "ufc_fighter": ufc_fighter,
            "matches": top_matches,
        }

    def _extract_sherdog_data(self, row_selector: scrapy.Selector) -> dict[str, Any] | None:
        """Extract fighter data from a Sherdog search result row.

        Args:
            row_selector: Scrapy selector for the result row

        Returns:
            Dictionary with fighter data or None if extraction failed
        """
        try:
            # Try to extract fighter URL (contains Sherdog ID)
            fighter_link = row_selector.css("a[href*='/fighter/']::attr(href)").get()

            if not fighter_link:
                return None

            # Extract Sherdog ID from URL (e.g., /fighter/Jon-Jones-27944 -> 27944)
            sherdog_id = None
            if fighter_link:
                parts = fighter_link.rstrip("/").split("-")
                if parts:
                    try:
                        sherdog_id = int(parts[-1])
                    except ValueError:
                        pass

            # Extract fighter name
            name = row_selector.css("a[href*='/fighter/']::text").get()
            if name:
                name = name.strip()

            # Extract division/weight class
            # Sherdog typically shows this in a cell or span
            division = row_selector.css("td.weight::text").get()
            if not division:
                division = row_selector.css("span.weight_class::text").get()
            if division:
                division = division.strip()

            # Extract record (format: "W-L-D")
            # Usually in a cell or span with record data
            record = row_selector.css("td.record::text").get()
            if not record:
                record = row_selector.css("span.record::text").get()
            if record:
                record = record.strip()

            # Construct full URL
            full_url = None
            if fighter_link:
                if fighter_link.startswith("http"):
                    full_url = fighter_link
                else:
                    full_url = f"https://www.sherdog.com{fighter_link}"

            return {
                "sherdog_id": sherdog_id,
                "url": full_url,
                "name": name,
                "division": division,
                "record": record,
            }

        except Exception as e:
            logger.warning(f"Error extracting Sherdog data from row: {e}")
            return None

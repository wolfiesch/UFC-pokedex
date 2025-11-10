"""Scrapy spider for scraping UFC official rankings from UFC.com.

This spider fetches the current official UFC rankings organized by weight class
from https://www.ufc.com/rankings. It extracts champion and ranked fighters (1-15)
for each division.
"""

from __future__ import annotations

from datetime import date

import scrapy

from scraper.config import settings
from scraper.models.fighter import FighterRankingItem
from scraper.utils.ufc_rankings_parser import parse_ufc_rankings_page


class UfcRankingsSpider(scrapy.Spider):
    """Spider to scrape UFC.com official rankings."""

    name = "ufc_rankings"
    allowed_domains = ["ufc.com"]
    custom_settings = {
        "DOWNLOAD_DELAY": settings.delay_seconds,
        "USER_AGENT": settings.user_agent,
        "AUTOTHROTTLE_ENABLED": True,
        "CONCURRENT_REQUESTS": 1,  # UFC.com rankings is a single page
    }

    def start_requests(self):
        """Start scraping from UFC.com rankings page."""
        url = "https://www.ufc.com/rankings"
        yield scrapy.Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response: scrapy.http.Response):
        """Parse UFC rankings page and extract all divisions.

        Args:
            response: Scrapy response from UFC.com rankings page

        Yields:
            FighterRankingItem for each ranked fighter
        """
        self.logger.info(f"Parsing UFC rankings from {response.url}")

        # Parse HTML to extract rankings
        rank_date = date.today()
        rankings_data = parse_ufc_rankings_page(response.text, rank_date)

        self.logger.info(f"Found {len(rankings_data)} ranking entries")

        # Convert to Pydantic models and yield
        for ranking_dict in rankings_data:
            try:
                ranking_item = FighterRankingItem(**ranking_dict)
                yield ranking_item
            except Exception as e:
                self.logger.error(
                    f"Failed to create FighterRankingItem from {ranking_dict}: {e}"
                )

        self.logger.info("Finished parsing UFC rankings")

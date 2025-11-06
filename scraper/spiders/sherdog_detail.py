"""Spider to scrape detailed fighter information from Sherdog profiles."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import scrapy

from scraper.config import settings
from scraper.utils.sherdog_parser import parse_sherdog_fighter_detail

logger = logging.getLogger(__name__)


class SherdogDetailSpider(scrapy.Spider):
    """Scrape detailed fighter stats from Sherdog profile pages.

    This spider loads the Sherdog matches JSON, filters for high-confidence matches
    (≥70%), and scrapes each fighter's Sherdog profile page to extract:
    - Date of Birth (DOB)
    - Height
    - Weight
    - Reach
    - Stance
    - Nationality

    Input:
        data/processed/sherdog_matches.json - UFC ID -> Sherdog matches with confidence
            Format: {"ufc_id": {"ufc_fighter": {...}, "matches": [...]}}

    Output:
        data/processed/sherdog_fighter_details.jsonl - One fighter per line
            Format: {"ufc_id": "...", "sherdog_id": 123, "dob": "...", "height": "...", ...}
    """

    name = "sherdog_detail"
    allowed_domains = ["sherdog.com"]
    custom_settings = {
        "DOWNLOAD_DELAY": settings.delay_seconds,
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2.0,
        "AUTOTHROTTLE_MAX_DELAY": 10.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 2.0,
        # Use validation and storage pipelines
        "ITEM_PIPELINES": {
            "scraper.pipelines.validation.ValidationPipeline": 100,
            "scraper.pipelines.storage.StoragePipeline": 200,
        },
    }

    def __init__(self, min_confidence: float = 70.0, *args, **kwargs):
        """Initialize spider.

        Args:
            min_confidence: Minimum confidence score to scrape (default: 70.0)
        """
        super().__init__(*args, **kwargs)
        self.min_confidence = float(min_confidence)
        self.matches_file = Path("data/processed/sherdog_matches.json")

    def start_requests(self):
        """Load Sherdog matches and initiate detail page requests."""
        if not self.matches_file.exists():
            logger.error(f"Matches file not found: {self.matches_file}")
            logger.error("Please run: make scrape-sherdog-search first")
            return

        with self.matches_file.open() as f:
            matches = json.load(f)

        logger.info(f"Loaded {len(matches)} fighter matches")

        # Filter for high-confidence matches
        high_confidence_count = 0
        skipped_count = 0

        for ufc_id, match_data in matches.items():
            ufc_fighter = match_data["ufc_fighter"]
            top_matches = match_data.get("matches", [])

            if not top_matches:
                skipped_count += 1
                continue

            best_match = top_matches[0]
            confidence = best_match["confidence"]

            if confidence < self.min_confidence:
                skipped_count += 1
                continue

            sherdog_url = best_match.get("sherdog_url")
            sherdog_id = best_match.get("sherdog_id")

            if not sherdog_url or not sherdog_id:
                logger.warning(f"Missing Sherdog URL or ID for {ufc_fighter['name']}")
                skipped_count += 1
                continue

            high_confidence_count += 1

            yield scrapy.Request(
                sherdog_url,
                callback=self.parse_fighter_detail,
                meta={
                    "ufc_id": ufc_id,
                    "ufc_fighter": ufc_fighter,
                    "sherdog_id": sherdog_id,
                    "confidence": confidence,
                },
                dont_filter=True,
                errback=self.handle_error,
            )

        logger.info(
            f"Scraping {high_confidence_count} fighters with confidence ≥{self.min_confidence}%"
        )
        logger.info(f"Skipped {skipped_count} fighters (low confidence or missing data)")

    def parse_fighter_detail(self, response: scrapy.http.Response):
        """Parse Sherdog fighter detail page.

        Args:
            response: Scrapy response from Sherdog fighter page
        """
        ufc_id = response.meta["ufc_id"]
        ufc_fighter = response.meta["ufc_fighter"]
        sherdog_id = response.meta["sherdog_id"]
        confidence = response.meta["confidence"]

        try:
            # Parse the fighter detail page
            fighter_data = parse_sherdog_fighter_detail(response)

            if not fighter_data:
                logger.warning(f"Could not parse Sherdog data for {ufc_fighter['name']}")
                return

            # Add metadata
            fighter_data["ufc_id"] = ufc_id
            fighter_data["sherdog_id"] = sherdog_id
            fighter_data["sherdog_url"] = response.url
            fighter_data["match_confidence"] = confidence
            fighter_data["ufc_name"] = ufc_fighter["name"]
            fighter_data["item_type"] = "sherdog_fighter_detail"

            logger.info(
                f"Scraped {ufc_fighter['name']} - "
                f"DOB: {fighter_data.get('dob', 'N/A')}, "
                f"Height: {fighter_data.get('height', 'N/A')}, "
                f"Reach: {fighter_data.get('reach', 'N/A')}"
            )

            yield fighter_data

        except Exception as e:
            logger.error(f"Error parsing {ufc_fighter['name']} at {response.url}: {e}")

    def handle_error(self, failure):
        """Handle request errors.

        Args:
            failure: Twisted Failure object
        """
        request = failure.request
        ufc_fighter = request.meta.get("ufc_fighter", {})
        fighter_name = ufc_fighter.get("name", "Unknown")

        logger.error(f"Request failed for {fighter_name}: {failure.value}")

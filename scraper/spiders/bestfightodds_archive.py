from __future__ import annotations

import re
from datetime import datetime

import scrapy

from scraper.config import settings


class BestFightOddsArchiveSpider(scrapy.Spider):
    """
    Spider to scrape the Best Fight Odds archive page for UFC events.

    This spider collects:
    - Event names and dates
    - Event URLs for detailed scraping

    Usage:
        scrapy crawl bestfightodds_archive -o data/raw/bfo_events_archive.jsonl
    """

    name = "bestfightodds_archive"
    allowed_domains = ["bestfightodds.com"]

    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,  # Be respectful to the server
        "USER_AGENT": settings.user_agent,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1.0,
        "AUTOTHROTTLE_MAX_DELAY": 5.0,
        "ITEM_PIPELINES": {},  # Disable pipelines for this spider
    }

    def start_requests(self):
        """Start by requesting the archive page."""
        yield scrapy.Request(
            url="https://www.bestfightodds.com/archive",
            callback=self.parse,
            dont_filter=True,
        )

    def parse(self, response: scrapy.http.Response):
        """
        Parse the archive page to extract event information.

        The archive page contains a list of recent events with:
        - Date (e.g., "Nov 9th 2025")
        - Event name and URL (e.g., "/events/ufc-vegas-111-3917")
        """
        # Find all event rows in the content list table
        event_rows = response.css("table.content-list tr")

        for row in event_rows:
            # Extract date
            date_text = row.css("td.content-list-date::text").get()
            if not date_text:
                continue

            # Extract event title and URL
            event_link = row.css("td.content-list-title a")
            event_title = event_link.css("::text").get()
            event_url = event_link.css("::attr(href)").get()

            if not event_title or not event_url:
                continue

            # Parse the event URL to extract event ID
            # URL format: /events/ufc-vegas-111-3917
            event_id_match = re.search(r'/events/(.+-(\d+))$', event_url)
            event_id = event_id_match.group(1) if event_id_match else None
            event_numeric_id = event_id_match.group(2) if event_id_match else None

            # Filter for UFC events only (skip other promotions)
            organization = self._extract_organization(event_title)

            # Parse the date
            parsed_date = self._parse_date(date_text)

            yield {
                "event_id": event_id,
                "event_numeric_id": event_numeric_id,
                "event_title": event_title.strip(),
                "event_date": parsed_date,
                "event_url": response.urljoin(event_url),
                "organization": organization,
                "scraped_at": datetime.utcnow().isoformat(),
            }

    def _extract_organization(self, title: str) -> str:
        """Extract the organization name from the event title."""
        title_upper = title.upper()
        if "UFC" in title_upper:
            return "UFC"
        elif "BELLATOR" in title_upper:
            return "Bellator"
        elif "PFL" in title_upper:
            return "PFL"
        elif "ONE" in title_upper:
            return "ONE Championship"
        elif "RIZIN" in title_upper:
            return "Rizin"
        else:
            # Try to extract the first word/acronym as organization
            first_word = title.split()[0] if title else "Unknown"
            return first_word

    def _parse_date(self, date_text: str) -> str | None:
        """
        Parse date string like 'Nov 9th 2025' into ISO format.

        Args:
            date_text: Date string from the archive page

        Returns:
            ISO formatted date string (YYYY-MM-DD) or None if parsing fails
        """
        if not date_text:
            return None

        try:
            # Remove ordinal suffixes (st, nd, rd, th)
            cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_text.strip())
            # Parse with strptime
            dt = datetime.strptime(cleaned, "%b %d %Y")
            return dt.date().isoformat()
        except (ValueError, AttributeError) as e:
            self.logger.warning(f"Failed to parse date '{date_text}': {e}")
            return None

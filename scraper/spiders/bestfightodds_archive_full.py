from __future__ import annotations

import re
from datetime import datetime

import scrapy

from scraper.config import settings


class BestFightOddsArchiveFullSpider(scrapy.Spider):
    """
    Spider to scrape the complete Best Fight Odds archive by crawling event IDs.

    This spider discovers historical events by iterating through numeric event IDs
    from a specified range. Based on research:
    - ID 98: UFC 91 (Nov 2008) - one of the earliest UFC events with odds
    - ID 1837: UFC 247 (Feb 2020)
    - ID 2033: UFC 258 (Feb 2021)
    - ID 3917-3939: Current events (Nov 2025)

    The spider will:
    1. Iterate through event IDs from start_id to end_id
    2. Extract event metadata from each valid event page
    3. Filter for UFC events only (configurable via organization parameter)
    4. Handle 404s gracefully for missing IDs

    Usage:
        # Scrape all events from ID 1 to 4000 (all promotions)
        scrapy crawl bestfightodds_archive_full -o data/raw/bfo_events_archive_full.jsonl

        # Scrape specific ID range
        scrapy crawl bestfightodds_archive_full -a start_id=1000 -a end_id=2000

        # Scrape only UFC events
        scrapy crawl bestfightodds_archive_full -a organization=UFC

        # Scrape recent events (last 500 IDs)
        scrapy crawl bestfightodds_archive_full -a start_id=3500 -a end_id=4000
    """

    name = "bestfightodds_archive_full"
    allowed_domains = ["bestfightodds.com"]

    custom_settings = {
        "DOWNLOAD_DELAY": 1.0,  # Be respectful but faster than archive spider
        "USER_AGENT": settings.user_agent,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 0.5,
        "AUTOTHROTTLE_MAX_DELAY": 3.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 2.0,
        "CONCURRENT_REQUESTS": 4,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 2,
        "ITEM_PIPELINES": {},  # Disable pipelines for this spider
        "HTTPERROR_ALLOW_ALL": True,  # Handle 404s in parse method
    }

    def __init__(
        self,
        start_id: str = "1",
        end_id: str = "4000",
        organization: str | None = None,
        *args,
        **kwargs,
    ):
        """
        Initialize the spider with ID range and optional organization filter.

        Args:
            start_id: Starting event ID (default: 1)
            end_id: Ending event ID (default: 4000)
            organization: Filter for specific organization (e.g., "UFC", "Bellator")
        """
        super().__init__(*args, **kwargs)
        self.start_id = int(start_id)
        self.end_id = int(end_id)
        self.organization_filter = organization

        self.logger.info(
            f"Configured to scrape event IDs {self.start_id} to {self.end_id}"
        )
        if self.organization_filter:
            self.logger.info(f"Filtering for organization: {self.organization_filter}")

        # Track statistics
        self.stats = {
            "total_requests": 0,
            "successful_events": 0,
            "not_found": 0,
            "filtered_out": 0,
        }

    def start_requests(self):
        """Generate requests for all event IDs in the specified range."""
        for event_id in range(self.start_id, self.end_id + 1):
            self.stats["total_requests"] += 1

            # Progress logging every 100 events
            if event_id % 100 == 0:
                self.logger.info(
                    f"Progress: Requesting ID {event_id} "
                    f"({self.stats['successful_events']} events found, "
                    f"{self.stats['not_found']} not found)"
                )

            yield scrapy.Request(
                url=f"https://www.bestfightodds.com/events/{event_id}",
                callback=self.parse,
                errback=self.errback_httpbin,
                meta={"event_id": event_id},
                dont_filter=True,
            )

    def parse(self, response: scrapy.http.Response):
        """
        Parse an event page to extract event information.

        The event page contains:
        - Event title (e.g., "UFC Vegas 111")
        - Event date
        - Fight matchups with odds
        """
        event_id = response.meta["event_id"]

        # Handle 404s and other errors
        if response.status == 404:
            self.stats["not_found"] += 1
            self.logger.debug(f"Event ID {event_id} not found (404)")
            return

        if response.status != 200:
            self.logger.warning(
                f"Event ID {event_id} returned status {response.status}"
            )
            return

        # Detect redirects to homepage (invalid event IDs redirect to homepage)
        if response.url == "https://www.bestfightodds.com/" or \
           "/events/" not in response.url:
            self.stats["not_found"] += 1
            self.logger.debug(f"Event ID {event_id} redirected to homepage (invalid ID)")
            return

        # Extract event title from page
        event_title = self._extract_event_title(response)
        if not event_title:
            self.logger.warning(f"Could not extract title for event ID {event_id}")
            return

        # Extract organization from title
        organization = self._extract_organization(event_title)

        # Filter by organization if specified
        if self.organization_filter and organization != self.organization_filter:
            self.stats["filtered_out"] += 1
            self.logger.debug(
                f"Filtered out {event_title} (org: {organization}, "
                f"looking for: {self.organization_filter})"
            )
            return

        # Extract event date
        event_date = self._extract_event_date(response)

        # Extract event slug from URL if available
        event_slug = self._extract_event_slug(response.url)

        self.stats["successful_events"] += 1

        yield {
            "event_id": str(event_id),
            "event_numeric_id": event_id,
            "event_title": event_title.strip(),
            "event_date": event_date,
            "event_url": response.url,
            "event_slug": event_slug,
            "organization": organization,
            "scraped_at": datetime.utcnow().isoformat(),
        }

    def errback_httpbin(self, failure):
        """Handle request failures."""
        self.logger.debug(f"Request failed: {failure.request.url}")

    def closed(self, reason):
        """Log final statistics when spider closes."""
        self.logger.info("=" * 70)
        self.logger.info("SCRAPING COMPLETE")
        self.logger.info("=" * 70)
        self.logger.info(f"Total requests: {self.stats['total_requests']}")
        self.logger.info(f"Successful events: {self.stats['successful_events']}")
        self.logger.info(f"Not found (404): {self.stats['not_found']}")
        self.logger.info(f"Filtered out: {self.stats['filtered_out']}")
        self.logger.info("=" * 70)

    def _extract_event_title(self, response: scrapy.http.Response) -> str | None:
        """
        Extract the event title from the page.

        Multiple strategies:
        1. Look for page title or H1
        2. Look for event heading in the content area
        3. Extract from breadcrumbs
        """
        # Strategy 1: Page title
        title = response.css("title::text").get()
        if title:
            # Clean up title (remove " Odds" suffix)
            title = title.replace(" Odds", "").replace(" | Best Fight Odds", "").strip()
            if title and title != "Best Fight Odds":
                return title

        # Strategy 2: H1 heading
        h1 = response.css("h1::text").get()
        if h1:
            return h1.strip()

        # Strategy 3: Event name in breadcrumb or content
        event_name = response.css(".event-name::text, .event-title::text").get()
        if event_name:
            return event_name.strip()

        return None

    def _extract_event_date(self, response: scrapy.http.Response) -> str | None:
        """
        Extract the event date from the page.

        Look for date elements in the page, which typically show
        the event date in formats like "Nov 9th 2025".
        """
        # Look for date in various possible selectors
        date_selectors = [
            ".event-date::text",
            ".date::text",
            'time::attr(datetime)',
            'meta[property="article:published_time"]::attr(content)',
        ]

        for selector in date_selectors:
            date_text = response.css(selector).get()
            if date_text:
                parsed_date = self._parse_date(date_text)
                if parsed_date:
                    return parsed_date

        # Try to extract from page content using regex
        # Look for patterns like "Nov 9th 2025" or "November 9, 2025"
        text_content = " ".join(response.css("body *::text").getall())
        date_pattern = r'(\w+ \d{1,2}(?:st|nd|rd|th)?,? \d{4})'
        matches = re.findall(date_pattern, text_content)
        if matches:
            parsed_date = self._parse_date(matches[0])
            if parsed_date:
                return parsed_date

        return None

    def _extract_event_slug(self, url: str) -> str | None:
        """
        Extract the event slug from the URL.

        URL format: https://www.bestfightodds.com/events/ufc-vegas-111-3917
        Extract: ufc-vegas-111-3917
        """
        match = re.search(r'/events/([^/]+)$', url)
        if match:
            return match.group(1)
        return None

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
        Parse date string into ISO format.

        Handles formats like:
        - 'Nov 9th 2025'
        - 'November 9, 2025'
        - ISO format strings
        """
        if not date_text:
            return None

        try:
            # Try ISO format first
            if "T" in date_text:
                dt = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
                return dt.date().isoformat()

            # Remove ordinal suffixes (st, nd, rd, th)
            cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_text.strip())
            # Remove commas
            cleaned = cleaned.replace(',', '')

            # Try different date formats
            for fmt in ["%b %d %Y", "%B %d %Y", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(cleaned, fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue

        except (ValueError, AttributeError) as e:
            self.logger.debug(f"Failed to parse date '{date_text}': {e}")

        return None

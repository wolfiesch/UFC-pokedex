"""UFC.com athletes list spider.

This spider scrapes the UFC.com athletes list from the HTML page.
It extracts athlete slugs from profile links for later detailed scraping.

Note: The JSON API endpoint is blocked by robots.txt, so we scrape HTML instead.
"""

from __future__ import annotations

from pathlib import Path

import scrapy

from scraper.models.ufc_com import UFCComAthleteListItem


class UFCComAthletesSpider(scrapy.Spider):
    """Spider for scraping UFC.com athletes list.

    Scrapes the HTML athletes page to extract fighter slugs.
    The slugs are used by the athlete_detail spider to fetch full profiles.

    Output:
        - data/processed/ufc_com_athletes_list.jsonl (list of slugs)
        - data/raw/ufc_com/athletes_page.html (raw HTML page)
    """

    name = "ufc_com_athletes"
    allowed_domains = ["ufc.com"]

    custom_settings = {
        # Download delay: 15 seconds (required by robots.txt)
        "DOWNLOAD_DELAY": 15.0,
        # Randomize to appear human-like (11.25s - 18.75s)
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        # Only 1 concurrent request to UFC.com
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        # AutoThrottle: Adapt to server speed
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 15.0,
        "AUTOTHROTTLE_MAX_DELAY": 60.0,
        # User agent
        "USER_AGENT": "UFC-Pokedex-Bot/1.0 (+https://github.com/user/ufc-pokedex)",
        # Respect robots.txt
        "ROBOTSTXT_OBEY": True,
        # Retry on rate limits
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        # HTTP caching (avoid re-scraping)
        "HTTPCACHE_ENABLED": True,
        "HTTPCACHE_EXPIRATION_SECS": 86400,  # 24 hours
        # Disable default pipelines (we'll handle storage manually)
        "ITEM_PIPELINES": {},
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure output directories exist
        self.raw_output_dir = Path("data/raw/ufc_com")
        self.raw_output_dir.mkdir(parents=True, exist_ok=True)

        self.processed_output_dir = Path("data/processed")
        self.processed_output_dir.mkdir(parents=True, exist_ok=True)

        self.output_file = self.processed_output_dir / "ufc_com_athletes_list.jsonl"
        # Clear output file if it exists
        if self.output_file.exists():
            self.output_file.unlink()

    def start_requests(self):
        """Start scraping the athletes page (HTML version).

        Note: We scrape the HTML page instead of the JSON API because
        the API endpoint is blocked by robots.txt.
        """
        # The athletes page shows all fighters on a single page (no pagination)
        url = "https://www.ufc.com/athletes/all"
        yield scrapy.Request(
            url,
            callback=self.parse,
            dont_filter=True,
        )

    def parse(self, response: scrapy.http.Response):
        """Parse athletes from the HTML page.

        The page contains links to athlete profiles in the format:
        /athlete/{slug}
        """
        # Save raw HTML response
        raw_file = self.raw_output_dir / "athletes_page.html"
        raw_file.write_bytes(response.body)

        # Extract all athlete links
        athlete_links = response.css('a[href*="/athlete/"]::attr(href)').getall()

        # Filter to get unique slugs
        slugs_seen = set()
        count = 0

        for link in athlete_links:
            # Extract slug from URL (/athlete/{slug})
            if "/athlete/" in link:
                slug = link.split("/athlete/")[-1].split("?")[0].split("#")[0]

                # Skip duplicates and invalid slugs
                if not slug or slug in slugs_seen:
                    continue

                # Skip image URLs
                if slug.endswith(".png") or slug.endswith(".jpg"):
                    continue

                slugs_seen.add(slug)

                try:
                    # Create item with minimal data
                    # (full data will be scraped by athlete_detail spider)
                    item = UFCComAthleteListItem(
                        name=slug.replace("-", " ").title(),  # Approximate name from slug
                        slug=slug,
                        profile_url=f"https://www.ufc.com/athlete/{slug}",
                    )

                    # Write to JSONL immediately
                    self._write_to_jsonl(item)
                    yield item.model_dump()

                    count += 1

                except Exception as e:
                    self.logger.error(f"Failed to create item for slug {slug}: {e}")
                    continue

        self.logger.info(f"Found {count} unique athlete slugs")

    def _write_to_jsonl(self, item: UFCComAthleteListItem):
        """Write a single item to the JSONL output file."""
        with open(self.output_file, "a") as f:
            f.write(item.model_dump_json() + "\n")

"""UFC.com athlete detail spider.

This spider scrapes individual UFC.com athlete profile pages to extract
biographical data including birthplace and training gym information.
"""

from __future__ import annotations

import json
from pathlib import Path

import scrapy

from scraper.models.ufc_com import UFCComAthleteDetail


class UFCComAthleteDetailSpider(scrapy.Spider):
    """Spider for scraping individual UFC.com athlete profiles.

    This spider can be run in two modes:
    1. With input file: -a input=data/processed/ufc_com_athletes_list.jsonl
    2. With slugs: -a slugs=conor-mcgregor,israel-adesanya

    Output:
        - data/processed/ufc_com_fighters/{slug}.json (individual files)
    """

    name = "ufc_com_athlete_detail"
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

    def __init__(self, input=None, slugs=None, *args, **kwargs):
        """Initialize spider with input source.

        Args:
            input: Path to JSONL file with athlete list
            slugs: Comma-separated list of slugs to scrape
        """
        super().__init__(*args, **kwargs)

        # Ensure output directory exists
        self.output_dir = Path("data/processed/ufc_com_fighters")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load slugs from input source
        self.slugs = []
        if input:
            self._load_slugs_from_file(input)
        elif slugs:
            self.slugs = [s.strip() for s in slugs.split(",")]
        else:
            self.logger.warning(
                "No input source provided! Use -a input=file.jsonl or -a slugs=slug1,slug2"
            )

        self.logger.info(f"Loaded {len(self.slugs)} fighters to scrape")

    def _load_slugs_from_file(self, input_file: str):
        """Load fighter slugs from JSONL input file."""
        input_path = Path(input_file)
        if not input_path.exists():
            self.logger.error(f"Input file not found: {input_file}")
            return

        with open(input_path) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    slug = data.get("slug")
                    if slug:
                        self.slugs.append(slug)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse line: {e}")
                    continue

    def start_requests(self):
        """Generate requests for each fighter slug."""
        for slug in self.slugs:
            url = f"https://www.ufc.com/athlete/{slug}"
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta={"slug": slug},
                dont_filter=True,
            )

    def parse(self, response: scrapy.http.Response):
        """Parse athlete profile page and extract biographical data.

        Extracts data from .c-bio__row elements:
        - Place of Birth
        - Trains at
        - Age
        - Height
        - Weight
        - Status
        """
        slug = response.meta["slug"]

        # Parse bio fields
        bio_data = self._parse_bio(response)

        # Add slug and name
        bio_data["slug"] = slug
        bio_data["name"] = self._extract_name(response)

        # Create Pydantic model
        try:
            item = UFCComAthleteDetail(**bio_data)

            # Save to individual JSON file
            output_file = self.output_dir / f"{slug}.json"
            output_file.write_text(item.model_dump_json(indent=2))

            self.logger.info(f"Saved {slug}: birthplace={item.birthplace}, gym={item.training_gym}")

            yield item.model_dump()

        except Exception as e:
            self.logger.error(f"Failed to create model for {slug}: {e}")
            self.logger.debug(f"Bio data: {bio_data}")

    def _extract_name(self, response: scrapy.http.Response) -> str:
        """Extract fighter name from page."""
        # Try multiple selectors
        name = (
            response.css(".hero-profile__name::text").get()
            or response.css("h1.hero-profile__name::text").get()
            or response.css(".c-hero__headline::text").get()
            or "Unknown"
        )
        return name.strip()

    def _parse_bio(self, response: scrapy.http.Response) -> dict:
        """Parse biographical fields from .c-bio__field elements.

        Returns:
            Dict with parsed bio fields
        """
        bio_data = {}

        # Find all bio fields
        bio_rows = response.css(".c-bio__field")

        for row in bio_rows:
            label = row.css(".c-bio__label::text").get()
            value = row.css(".c-bio__text::text").get()

            if not label or not value:
                continue

            label = label.strip()
            value = value.strip()

            # Parse birthplace
            if label == "Place of Birth":
                bio_data["birthplace"] = value

                # Split into city and country
                if "," in value:
                    parts = value.split(",", 1)
                    bio_data["birthplace_city"] = parts[0].strip()
                    bio_data["birthplace_country"] = parts[1].strip()
                else:
                    # Only country provided
                    bio_data["birthplace_country"] = value

            # Parse training gym
            elif label == "Trains at":
                bio_data["training_gym"] = value

            # Parse age
            elif label == "Age":
                try:
                    bio_data["age"] = int(value)
                except ValueError:
                    self.logger.debug(f"Failed to parse age: {value}")

            # Parse height
            elif label == "Height":
                bio_data["height"] = value

            # Parse weight
            elif label == "Weight":
                bio_data["weight"] = value

            # Parse status
            elif label == "Status":
                bio_data["status"] = value

        return bio_data

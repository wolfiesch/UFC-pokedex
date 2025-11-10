"""Fight Matrix rankings reconnaissance spider.

This spider captures HTML samples from Fight Matrix for analysis.
Used for Phase 3a recon - understanding site structure before building production scraper.

Usage:
    .venv/bin/scrapy crawl fightmatrix_recon -o /tmp/claude/fightmatrix_samples.json
"""

import scrapy
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class FightMatrixReconSpider(scrapy.Spider):
    """Reconnaissance spider to capture Fight Matrix HTML samples."""

    name = "fightmatrix_recon"
    allowed_domains = ["fightmatrix.com"]

    # Custom settings for polite scraping
    custom_settings = {
        "DOWNLOAD_DELAY": 3.0,  # 3 second delay between requests
        "CONCURRENT_REQUESTS": 1,  # One request at a time
        "ROBOTSTXT_OBEY": True,
        "USER_AGENT": "UFC-Pokedex-Research/0.1 (+https://github.com/wolfiesch/ufc-pokedex)",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Test divisions - sample a few key ones
        self.test_divisions = [
            "lightweight",
            "welterweight",
            "heavyweight",
            "womens-bantamweight",
        ]

    def start_requests(self):
        """Generate requests for current and historical rankings."""

        # 1. Current rankings for each test division
        for division in self.test_divisions:
            url = f"https://www.fightmatrix.com/mma-ranks/{division}/"
            yield scrapy.Request(
                url=url,
                callback=self.parse_current_rankings,
                meta={
                    "division": division,
                    "snapshot_type": "current",
                },
                dont_filter=True,
            )

        # 2. Historical rankings - sample dates
        # Get one sample each: 1 month ago, 6 months ago, 12 months ago
        today = datetime.now()
        sample_dates = [
            today - timedelta(days=30),   # 1 month ago
            today - timedelta(days=180),  # 6 months ago
            today - timedelta(days=365),  # 12 months ago
        ]

        for sample_date in sample_dates:
            # Fight Matrix uses format: YYYY-MM-DD
            date_str = sample_date.strftime("%Y-%m-%d")

            # Sample one division for historical (lightweight)
            url = (
                "https://www.fightmatrix.com/historical-mma-rankings/"
                f"generated-historical-rankings/?Issue={date_str}&Division=1"
            )
            yield scrapy.Request(
                url=url,
                callback=self.parse_historical_rankings,
                meta={
                    "division": "lightweight",
                    "snapshot_type": "historical",
                    "rank_date": date_str,
                },
                dont_filter=True,
            )

    def parse_current_rankings(self, response):
        """Parse current rankings page and capture structure."""
        division = response.meta["division"]

        logger.info(f"Captured current rankings HTML for {division}")

        yield {
            "snapshot_type": "current",
            "division": division,
            "url": response.url,
            "captured_at": datetime.now().isoformat(),
            "html_sample": response.text[:5000],  # First 5000 chars for analysis
            "full_html_length": len(response.text),

            # Capture key selectors found
            "has_table_tag": bool(response.css("table").get()),
            "has_tbody": bool(response.css("tbody").get()),
            "has_tr_rows": bool(response.css("tr").getall()),
            "row_count": len(response.css("tr").getall()),

            # Try to find rank elements
            "potential_rank_selectors": [
                len(response.css(".rank").getall()),
                len(response.css("[class*='rank']").getall()),
                len(response.css("td:first-child").getall()),
            ],

            # Try to find fighter name elements
            "potential_name_selectors": [
                len(response.css("a[href*='/fighter/']").getall()),
                len(response.css(".fighter-name").getall()),
                len(response.css("[class*='fighter']").getall()),
            ],

            # Pagination
            "has_pagination": bool(
                response.css("a[href*='page=']").get() or
                response.css(".pagination").get() or
                response.css("a:contains('>')").get()
            ),
        }

    def parse_historical_rankings(self, response):
        """Parse historical rankings page and capture structure."""
        division = response.meta["division"]
        rank_date = response.meta["rank_date"]

        logger.info(f"Captured historical rankings HTML for {division} on {rank_date}")

        yield {
            "snapshot_type": "historical",
            "division": division,
            "rank_date": rank_date,
            "url": response.url,
            "captured_at": datetime.now().isoformat(),
            "html_sample": response.text[:5000],  # First 5000 chars
            "full_html_length": len(response.text),

            # Check for date display
            "has_issue_date": bool(response.css("*:contains('Issue Date')").get()),
            "has_release_number": bool(response.css("*:contains('Release')").get()),

            # Same structure checks as current
            "has_table_tag": bool(response.css("table").get()),
            "has_tbody": bool(response.css("tbody").get()),
            "has_tr_rows": bool(response.css("tr").getall()),
            "row_count": len(response.css("tr").getall()),

            # Form/dropdown elements for date selection
            "has_date_form": bool(response.css("form").get() or response.css("select").get()),
            "dropdown_count": len(response.css("select").getall()),
        }

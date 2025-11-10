"""
Fight Matrix Division Code Mapper Spider

Purpose: Discover division numeric codes by testing each dropdown option.
Output: Division name → Division code mapping (JSON)

Usage:
    .venv/bin/scrapy crawl fightmatrix_division_mapper -o data/processed/division_codes.json
"""

import scrapy
from typing import Generator


class FightMatrixDivisionMapperSpider(scrapy.Spider):
    """
    Spider to map Fight Matrix division names to their numeric codes.

    Strategy:
    1. Load the historical rankings page
    2. Extract all division dropdown options
    3. For each division, construct test URL with Issue 996
    4. Verify the URL loads successfully
    5. Extract confirmed division code from URL
    6. Output mapping as JSON
    """

    name = "fightmatrix_division_mapper"
    allowed_domains = ["www.fightmatrix.com"]

    # Start with known working Issue number
    BASE_URL = "https://www.fightmatrix.com/historical-mma-rankings/ranking-snapshots/"
    TEST_ISSUE = 996  # Known valid issue from reconnaissance

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS': 1,
        'ROBOTSTXT_OBEY': True,
        'USER_AGENT': 'UFC-Pokedex-Scraper/0.1 (+https://github.com/wolfiesch/UFC-pokedex)',
    }

    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """Start by fetching the base page to get all division options."""
        yield scrapy.Request(
            url=self.BASE_URL,
            callback=self.parse_division_dropdown,
            errback=self.handle_error
        )

    def parse_division_dropdown(self, response: scrapy.http.Response) -> Generator[scrapy.Request, None, None]:
        """
        Extract all division options from dropdown and test each one.

        Args:
            response: The base historical rankings page

        Yields:
            Requests to test each division code
        """
        # Get division-specific dropdown (second select on page)
        # First select is Issue dropdown, second is Division dropdown
        division_select = response.css('select')[1] if len(response.css('select')) > 1 else response.css('select')[0]
        division_options = division_select.css('option')

        # Extract division names and skip the placeholder option
        divisions_to_test = []
        for option in division_options:
            text = option.css('::text').get()
            if text and text.strip() and '- Select' not in text:
                divisions_to_test.append(text.strip())

        self.logger.info(f"Found {len(divisions_to_test)} divisions to test")

        # Test each division with known Issue number
        for division_code, division_name in enumerate(divisions_to_test, start=1):
            test_url = f"{self.BASE_URL}?Issue={self.TEST_ISSUE}&Division={division_code}"

            self.logger.info(f"Testing: {division_name} → Code {division_code}")

            yield scrapy.Request(
                url=test_url,
                callback=self.verify_division_code,
                cb_kwargs={
                    'division_name': division_name,
                    'division_code': division_code
                },
                errback=self.handle_error,
                dont_filter=True  # Allow multiple requests to same domain
            )

    def verify_division_code(
        self,
        response: scrapy.http.Response,
        division_name: str,
        division_code: int
    ) -> dict:
        """
        Verify the division code by checking if rankings table has data.

        Args:
            response: The division-specific rankings page
            division_name: Name of the division from dropdown
            division_code: Numeric code being tested

        Yields:
            Dictionary with division mapping if valid
        """
        # Check if rankings table has data (tbody with tr elements)
        rankings_table = response.css('table')[1] if len(response.css('table')) > 1 else None

        if rankings_table:
            fighter_rows = rankings_table.css('tbody tr')
            has_data = len(fighter_rows) > 0
        else:
            has_data = False

        # Extract actual division name from page title (for verification)
        page_title = response.css('title::text').get() or ''

        result = {
            'division_name': division_name.strip(),
            'division_code': division_code,
            'verified': has_data,
            'test_url': response.url,
            'page_title': page_title.strip(),
            'fighter_count': len(fighter_rows) if has_data else 0
        }

        if has_data:
            self.logger.info(
                f"✓ {division_name} → Code {division_code} "
                f"({len(fighter_rows)} fighters found)"
            )
        else:
            self.logger.warning(
                f"✗ {division_name} → Code {division_code} "
                f"(no data found - might be invalid)"
            )

        yield result

    def handle_error(self, failure):
        """Log errors during scraping."""
        self.logger.error(f"Request failed: {failure.request.url}")
        self.logger.error(f"Error: {failure.value}")

from __future__ import annotations

import scrapy

from scraper.config import settings
from scraper.utils.parser import parse_events_list_row


class EventsListSpider(scrapy.Spider):
    name = "events_list"
    allowed_domains = ["ufcstats.com"]
    custom_settings = {
        "DOWNLOAD_DELAY": settings.delay_seconds,
        "USER_AGENT": settings.user_agent,
        "AUTOTHROTTLE_ENABLED": True,
    }

    def start_requests(self):
        # Scrape both completed and upcoming events
        urls = [
            "http://ufcstats.com/statistics/events/completed?page=all",
            "http://ufcstats.com/statistics/events/upcoming",
        ]
        for url in urls:
            yield scrapy.Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response: scrapy.http.Response):
        # Parse table rows
        for row in response.css("tr.b-statistics__table-row"):
            item = parse_events_list_row(row)
            if item is not None:  # Skip rows that couldn't be parsed
                yield item

        # Follow pagination if it exists
        next_page = response.css("a.b-statistics__paginate-link.next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

from __future__ import annotations

import scrapy

from scraper.config import settings
from scraper.utils.parser import parse_fighter_list_row


class FightersListSpider(scrapy.Spider):
    name = "fighters_list"
    allowed_domains = ["ufcstats.com"]
    custom_settings = {
        "DOWNLOAD_DELAY": settings.delay_seconds,
        "USER_AGENT": settings.user_agent,
        "AUTOTHROTTLE_ENABLED": True,
    }

    def start_requests(self):
        base_url = "http://ufcstats.com/statistics/fighters"
        letters = list("abcdefghijklmnopqrstuvwxyz") + ["other"]
        for letter in letters:
            if letter == "other":
                url = f"{base_url}?char=other&page=all"
            else:
                url = f"{base_url}?char={letter}&page=all"
            yield scrapy.Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response: scrapy.http.Response):
        for row in response.css("tr.b-statistics__table-row"):
            item = parse_fighter_list_row(row)
            if item is not None:  # Skip rows that couldn't be parsed
                yield item

        next_page = response.css("a.b-statistics__paginate-link.next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

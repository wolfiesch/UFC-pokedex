from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import scrapy

from scraper.config import settings
from scraper.utils.parser import parse_event_detail_page


class EventDetailSpider(scrapy.Spider):
    name = "event_detail"
    allowed_domains = ["ufcstats.com"]

    custom_settings = {
        "DOWNLOAD_DELAY": settings.delay_seconds,
        "USER_AGENT": settings.user_agent,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 0.5,  # Start faster
        "AUTOTHROTTLE_MAX_DELAY": 3.0,  # Max delay cap
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 8.0,  # Target 8 concurrent requests
        "CONCURRENT_REQUESTS_PER_DOMAIN": settings.concurrent_requests,
    }

    def start_requests(self):
        for url in self._collect_event_urls():
            yield scrapy.Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response: scrapy.http.Response):
        yield parse_event_detail_page(response)

    # Helpers -----------------------------------------------------------------
    def _collect_event_urls(self) -> list[str]:
        urls: list[str] = []
        urls.extend(self._parse_arg_urls(getattr(self, "event_urls", None)))
        urls.extend(self._build_urls_from_ids(getattr(self, "event_ids", None)))
        urls.extend(self._load_urls_from_file(getattr(self, "input_file", None)))
        unique_urls = list(dict.fromkeys(urls))
        if not unique_urls:
            # Default to loading from events_list.jsonl if it exists
            default_file = Path("data/processed/events_list.jsonl")
            if default_file.exists():
                self.logger.info("Loading events from default file: %s", default_file)
                urls.extend(self._load_urls_from_file(str(default_file)))
                unique_urls = list(dict.fromkeys(urls))
            else:
                self.logger.warning(
                    "No event URLs provided; pass `-a event_ids=...`, `-a event_urls=...`, or `-a input_file=...`",
                )
        return unique_urls

    def _parse_arg_urls(self, arg: str | Iterable[str] | None) -> list[str]:
        if not arg:
            return []
        if isinstance(arg, str):
            return [url.strip() for url in arg.split(",") if url.strip()]
        return [url for url in arg if isinstance(url, str)]

    def _build_urls_from_ids(self, arg: str | Iterable[str] | None) -> list[str]:
        if not arg:
            return []
        if isinstance(arg, str):
            ids = [id_.strip() for id_ in arg.split(",") if id_.strip()]
        else:
            ids = [id_.strip() for id_ in arg if isinstance(id_, str)]
        return [f"http://ufcstats.com/event-details/{event_id}" for event_id in ids]

    def _load_urls_from_file(self, file_path: str | None) -> list[str]:
        if not file_path:
            return []
        path = Path(file_path)
        if not path.exists():
            self.logger.warning("Input file %s not found", file_path)
            return []
        urls: list[str] = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                detail_url = data.get("detail_url")
                if detail_url:
                    urls.append(detail_url)
        return urls

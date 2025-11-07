from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import scrapy

from scraper.config import settings
from scraper.utils.parser import parse_fighter_detail_page


class FighterDetailSpider(scrapy.Spider):
    name = "fighter_detail"
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
        for url in self._collect_fighter_urls():
            yield scrapy.Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response: scrapy.http.Response):
        yield parse_fighter_detail_page(response)

    # Helpers -----------------------------------------------------------------
    def _collect_fighter_urls(self) -> list[str]:
        urls: list[str] = []
        urls.extend(self._parse_arg_urls(getattr(self, "fighter_urls", None)))
        urls.extend(self._build_urls_from_ids(getattr(self, "fighter_ids", None)))
        urls.extend(self._load_urls_from_file(getattr(self, "input_file", None)))
        unique_urls = list(dict.fromkeys(urls))
        if not unique_urls:
            guidance = (
                "No fighter URLs provided; pass `-a fighter_ids=...`, "
                "`-a fighter_urls=...`, or `-a input_file=...`"
            )
            self.logger.warning(guidance)
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
        return [f"http://ufcstats.com/fighter-details/{fighter_id}" for fighter_id in ids]

    def _load_urls_from_file(self, file_path: str | None) -> list[str]:
        if not file_path:
            return []
        path = Path(file_path)
        if not path.exists():
            self.logger.warning("Input file %s not found", file_path)
            return []
        urls: list[str] = []
        with path.open(encoding="utf-8") as handle:
            for line_num, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as e:
                    self.logger.warning(
                        f"Skipping invalid JSON at line {line_num} in {file_path}: {e}"
                    )
                    continue
                detail_url = data.get("detail_url")
                if detail_url:
                    urls.append(detail_url)
        return urls

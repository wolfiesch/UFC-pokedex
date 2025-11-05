from __future__ import annotations

import asyncio
from collections.abc import Iterable
from pathlib import Path

import httpx
from scrapy.http import HtmlResponse

from scraper.config import settings
from scraper.utils.parser import parse_fighter_detail_page

SAMPLE_FIGHTERS: Iterable[str] = [
    "http://ufcstats.com/fighter-details/0472cd5b-5dcc-1bbb-aaaa-bbbbbbbbbbbb",
]


def _as_json(payload):
    import json

    return json.dumps(payload, indent=2)


async def fetch(url: str, client: httpx.AsyncClient) -> HtmlResponse:
    response = await client.get(url, timeout=30.0)
    response.raise_for_status()
    encoding = response.encoding or "utf-8"
    return HtmlResponse(url=url, body=response.content, encoding=encoding)


async def run_sample_scrape() -> None:
    output_dir = Path("data/samples")
    output_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(headers={"User-Agent": settings.user_agent}) as client:
        for url in SAMPLE_FIGHTERS:
            html_response = await fetch(url, client)
            fighter = parse_fighter_detail_page(html_response)
            path = output_dir / f"{fighter['fighter_id']}.json"
            path.write_text(_as_json(fighter), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(run_sample_scrape())

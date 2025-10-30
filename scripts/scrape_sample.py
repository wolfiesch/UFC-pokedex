"""Run a small targeted scrape for smoke testing."""

from __future__ import annotations

import asyncio

from scraper.runners.sample import run_sample_scrape


def main() -> None:
    asyncio.run(run_sample_scrape())


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ScraperSettings:
    base_url: str = "http://ufcstats.com"
    user_agent: str = os.getenv("SCRAPER_USER_AGENT", "UFC-Pokedex-Scraper/0.1 (+local)")
    delay_seconds: float = float(os.getenv("SCRAPER_DELAY_SECONDS", "1.5"))
    concurrent_requests: int = int(os.getenv("SCRAPER_CONCURRENT_REQUESTS", "4"))
    cache_dir: str = os.getenv("SCRAPER_CACHE_DIR", "data/cache")


settings = ScraperSettings()

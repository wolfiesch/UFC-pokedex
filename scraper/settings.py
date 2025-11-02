BOT_NAME = "ufc_pokedex"

SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 1.5
CONCURRENT_REQUESTS = 4
USER_AGENT = "UFC-Pokedex-Scraper/0.1 (+https://github.com/example/ufc-pokedex)"

ITEM_PIPELINES = {
    "scraper.pipelines.validation.ValidationPipeline": 100,
    "scraper.pipelines.storage.StoragePipeline": 200,
    "scraper.pipelines.sherdog_storage.SherdogStoragePipeline": 300,
}

LOG_LEVEL = "INFO"

# HTTP Caching - Avoid re-scraping already downloaded fighters
HTTPCACHE_ENABLED = True
HTTPCACHE_DIR = "data/cache/scrapy_cache"
HTTPCACHE_EXPIRATION_SECS = 86400  # 24 hours
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504]

# Connection pooling optimizations
REACTOR_THREADPOOL_MAXSIZE = 20
DNS_TIMEOUT = 10


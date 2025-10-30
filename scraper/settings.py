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
}

LOG_LEVEL = "INFO"


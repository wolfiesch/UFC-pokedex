"""Spider to download fighter images from Sherdog."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import scrapy

from scraper.config import settings

logger = logging.getLogger(__name__)


class SherdogImagesSpider(scrapy.Spider):
    """Download fighter images from Sherdog profiles.

    This spider loads the verified Sherdog ID mapping, visits each fighter's
    Sherdog profile page, extracts the image URL, and downloads the image.

    Input:
        data/sherdog_id_mapping.json - Verified UFC ID -> Sherdog ID mapping
            Format: {"ufc_id": {"sherdog_id": ..., "sherdog_url": ..., ...}}

    Output:
        data/images/fighters/{ufc_id}.jpg - Downloaded fighter images
        data/processed/sherdog_images.json - Image metadata
    """

    name = "sherdog_images"
    allowed_domains = ["sherdog.com"]
    custom_settings = {
        "DOWNLOAD_DELAY": settings.delay_seconds,
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2.0,
        "AUTOTHROTTLE_MAX_DELAY": 10.0,
        "IMAGES_STORE": "data/images",
        # Enable image pipeline
        "ITEM_PIPELINES": {
            "scrapy.pipelines.images.ImagesPipeline": 1,
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mapping_file = Path("data/sherdog_id_mapping.json")
        self.images_dir = Path("data/images/fighters")
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.image_metadata = {}

    def start_requests(self):
        """Load mapping and initiate Sherdog profile page requests."""
        if not self.mapping_file.exists():
            logger.error(f"Mapping file not found: {self.mapping_file}")
            logger.error("Please run: make verify-sherdog-matches first")
            return

        with self.mapping_file.open() as f:
            mapping = json.load(f)

        logger.info(f"Loaded mapping for {len(mapping)} fighters")

        for ufc_id, sherdog_data in mapping.items():
            sherdog_url = sherdog_data.get("sherdog_url")

            if not sherdog_url:
                logger.warning(f"No Sherdog URL for UFC fighter {ufc_id}")
                continue

            yield scrapy.Request(
                sherdog_url,
                callback=self.parse_fighter_page,
                meta={"ufc_id": ufc_id, "sherdog_data": sherdog_data},
                dont_filter=True,
            )

    def parse_fighter_page(self, response: scrapy.http.Response):
        """Parse Sherdog fighter page and extract image.

        Args:
            response: Scrapy response from Sherdog fighter page
        """
        ufc_id = response.meta["ufc_id"]
        sherdog_data = response.meta["sherdog_data"]

        # Find the fighter bio section with image
        bio_section = response.css("div.module.bio_fighter")

        if not bio_section:
            logger.warning(f"Could not find bio section for {ufc_id} at {response.url}")
            return

        # Extract image URL from bio section
        image_url = bio_section.css("img::attr(src)").get()

        if not image_url:
            logger.warning(f"No image found for {ufc_id} at {response.url}")
            return

        # Convert relative URL to absolute
        if image_url and not image_url.startswith("http"):
            image_url = f"https://www.sherdog.com{image_url}"

        logger.info(f"Found image for {ufc_id}: {image_url}")

        # Yield metadata
        yield {
            "ufc_id": ufc_id,
            "sherdog_id": sherdog_data.get("sherdog_id"),
            "image_url": image_url,
            "sherdog_url": response.url,
        }

        # Download image using scrapy's built-in image pipeline would be ideal,
        # but for simplicity, we'll use a custom download approach
        # Request the image and pass metadata
        yield scrapy.Request(
            image_url,
            callback=self.save_image,
            meta={"ufc_id": ufc_id, "image_url": image_url},
            dont_filter=True,
        )

    def save_image(self, response: scrapy.http.Response):
        """Save downloaded image to local filesystem.

        Args:
            response: Scrapy response containing image data
        """
        ufc_id = response.meta["ufc_id"]
        image_url = response.meta["image_url"]

        # Determine file extension from URL
        if image_url.lower().endswith(".png"):
            ext = "png"
        elif image_url.lower().endswith(".gif"):
            ext = "gif"
        else:
            ext = "jpg"

        # Save image
        image_path = self.images_dir / f"{ufc_id}.{ext}"

        try:
            with image_path.open("wb") as f:
                f.write(response.body)

            logger.info(f"Saved image for {ufc_id} to {image_path}")

            # Store metadata
            self.image_metadata[ufc_id] = {
                "image_path": str(image_path),
                "image_url": image_url,
                "file_size": len(response.body),
            }

        except Exception as e:
            logger.error(f"Error saving image for {ufc_id}: {e}")

    def closed(self, reason):
        """Called when spider closes; save image metadata."""
        metadata_file = Path("data/processed/sherdog_images.json")
        metadata_file.parent.mkdir(parents=True, exist_ok=True)

        with metadata_file.open("w") as f:
            json.dump(self.image_metadata, f, indent=2)

        logger.info(f"Saved metadata for {len(self.image_metadata)} images to {metadata_file}")

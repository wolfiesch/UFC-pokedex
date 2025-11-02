"""Storage pipeline for Sherdog search results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SherdogStoragePipeline:
    """Pipeline to aggregate Sherdog search results into a single JSON file."""

    def __init__(self) -> None:
        self.output_dir = Path("data/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / "sherdog_matches.json"
        self.matches: dict[str, Any] = {}

    def open_spider(self, spider):  # noqa: ANN001
        """Called when the spider opens."""
        # Initialize empty matches dict
        self.matches = {}

    def process_item(self, item: dict[str, Any], spider):  # noqa: ANN001
        """Aggregate Sherdog match results.

        Args:
            item: Match result containing ufc_id, ufc_fighter, and matches
            spider: The spider instance

        Returns:
            The item unchanged
        """
        if spider.name == "sherdog_search":
            ufc_id = item.get("ufc_id")
            if ufc_id:
                self.matches[ufc_id] = {
                    "ufc_fighter": item.get("ufc_fighter"),
                    "matches": item.get("matches", []),
                }

        return item

    def close_spider(self, spider):  # noqa: ANN001
        """Called when the spider closes; write aggregated results to JSON."""
        if spider.name == "sherdog_search" and self.matches:
            # Write all matches to a single JSON file
            with self.output_file.open("w", encoding="utf-8") as f:
                json.dump(self.matches, f, indent=2)

            spider.logger.info(
                f"Wrote {len(self.matches)} fighter matches to {self.output_file}"
            )

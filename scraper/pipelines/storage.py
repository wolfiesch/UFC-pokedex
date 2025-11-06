from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StoragePipeline:
    def __init__(self) -> None:
        self.output_dir = Path("data/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Fighter storage
        self.fighters_list_file = self.output_dir / "fighters_list.jsonl"
        self.fighters_detail_dir = self.output_dir / "fighters"
        self.fighters_detail_dir.mkdir(exist_ok=True)

        # Event storage
        self.events_list_file = self.output_dir / "events_list.jsonl"
        self.events_detail_dir = self.output_dir / "events"
        self.events_detail_dir.mkdir(exist_ok=True)

        # Sherdog fighter details storage
        self.sherdog_details_file = self.output_dir / "sherdog_fighter_details.jsonl"

        self._seen_fighters: set[str] = set()
        self._seen_events: set[str] = set()
        self._seen_sherdog_details: set[str] = set()

    def open_spider(self, spider):  # noqa: D401, ANN001
        """Called when the spider opens; rotate list file for fresh crawls."""
        spider_name = getattr(spider, "name", "")
        if spider_name == "fighters_list" and self.fighters_list_file.exists():
            backup_path = self.fighters_list_file.with_suffix(".jsonl.bak")
            self.fighters_list_file.rename(backup_path)
        elif spider_name == "events_list" and self.events_list_file.exists():
            backup_path = self.events_list_file.with_suffix(".jsonl.bak")
            self.events_list_file.rename(backup_path)
        self._seen_fighters.clear()
        self._seen_events.clear()

    def process_item(self, item: dict[str, Any], spider):  # noqa: D401, ANN001
        """Write validated item to disk for downstream use."""
        item_type = item.get("item_type")

        if item_type == "fighter_detail":
            fighter_id = item["fighter_id"]
            path = self.fighters_detail_dir / f"{fighter_id}.json"
            path.write_text(json.dumps(item, indent=2), encoding="utf-8")
        elif item_type == "sherdog_fighter_detail":
            ufc_id = item["ufc_id"]
            if ufc_id in self._seen_sherdog_details:
                return item
            self._seen_sherdog_details.add(ufc_id)
            with self.sherdog_details_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(item) + "\n")
        elif item_type == "event_detail":
            event_id = item["event_id"]
            path = self.events_detail_dir / f"{event_id}.json"
            path.write_text(json.dumps(item, indent=2), encoding="utf-8")
        elif item_type == "event_list":
            event_id = item["event_id"]
            if event_id in self._seen_events:
                return item
            self._seen_events.add(event_id)
            with self.events_list_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(item) + "\n")
        else:
            # Default to fighter list item
            fighter_id = item.get("fighter_id")
            if not fighter_id:
                return item
            if fighter_id in self._seen_fighters:
                return item
            self._seen_fighters.add(fighter_id)
            with self.fighters_list_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(item) + "\n")
        return item

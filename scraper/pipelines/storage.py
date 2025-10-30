from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StoragePipeline:
    def __init__(self) -> None:
        self.output_dir = Path("data/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.list_file = self.output_dir / "fighters_list.jsonl"
        self.detail_dir = self.output_dir / "fighters"
        self.detail_dir.mkdir(exist_ok=True)
        self._seen_fighters: set[str] = set()

    def open_spider(self, spider):  # noqa: D401, ANN001
        """Called when the spider opens; rotate list file for fresh crawls."""
        if getattr(spider, "name", "") == "fighters_list" and self.list_file.exists():
            backup_path = self.list_file.with_suffix(".jsonl.bak")
            self.list_file.rename(backup_path)
        self._seen_fighters.clear()

    def process_item(self, item: dict[str, Any], spider):  # noqa: D401, ANN001
        """Write validated item to disk for downstream use."""
        item_type = item.get("item_type")
        if item_type == "fighter_detail":
            fighter_id = item["fighter_id"]
            path = self.detail_dir / f"{fighter_id}.json"
            path.write_text(json.dumps(item, indent=2), encoding="utf-8")
        else:
            fighter_id = item["fighter_id"]
            if fighter_id in self._seen_fighters:
                return item
            self._seen_fighters.add(fighter_id)
            with self.list_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(item) + "\n")
        return item

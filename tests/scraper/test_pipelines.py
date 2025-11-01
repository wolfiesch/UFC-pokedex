from __future__ import annotations

import pytest

pytest.importorskip("itemadapter")

from scraper.pipelines.validation import ValidationPipeline


def test_validation_pipeline_preserves_item_type():
    pipeline = ValidationPipeline()
    item = {
        "item_type": "fighter_list",
        "fighter_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "detail_url": "http://ufcstats.com/fighter-details/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "John Doe",
        "nickname": None,
        "height": "6' 0\"",
        "weight": "185 lbs.",
        "division": "Middleweight",
        "reach": "75\"",
        "stance": "Orthodox",
        "dob": "1990-06-15",
    }

    validated = pipeline.process_item(item, spider=None)

    assert validated["item_type"] == "fighter_list"
    assert validated["fighter_id"] == item["fighter_id"]


def test_validation_pipeline_handles_detail_items():
    pipeline = ValidationPipeline()
    item = {
        "item_type": "fighter_detail",
        "fighter_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "detail_url": "http://ufcstats.com/fighter-details/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "John Doe",
        "nickname": "The Hammer",
        "record": "10-2-0",
        "height": "6' 0\"",
        "weight": "185 lbs.",
        "reach": "75\"",
        "leg_reach": "40\"",
        "stance": "Orthodox",
        "division": "Welterweight",
        "dob": "1990-06-15",
        "age": 33,
        "striking": {},
        "grappling": {},
        "significant_strikes": {},
        "takedown_stats": {},
        "fight_history": [],
    }

    validated = pipeline.process_item(item, spider=None)

    assert validated["item_type"] == "fighter_detail"
    assert validated["fight_history"] == []

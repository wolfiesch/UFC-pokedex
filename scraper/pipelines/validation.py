from __future__ import annotations

from itemadapter import ItemAdapter

from scraper.models.fighter import FighterDetail, FighterListItem


class ValidationPipeline:
    def process_item(self, item, spider):  # noqa: D401, ANN001
        """Validate scraped items using Pydantic models."""
        adapter = ItemAdapter(item)
        data = adapter.asdict()
        item_type = data.pop("item_type", None)

        if item_type == "fighter_detail":
            model = FighterDetail.model_validate(data)
        else:
            model = FighterListItem.model_validate(data)

        payload = model.model_dump(mode="json")
        if item_type:
            payload["item_type"] = item_type
        return payload

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Iterable

from parsel import Selector

logger = logging.getLogger(__name__)

UUID_RE = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
# Hex ID pattern for IDs without dashes (16 hex characters)
HEX_ID_RE = re.compile(r"([0-9a-f]{16})")


def _extract_uuid(url: str | None) -> str:
    if not url:
        raise ValueError("Missing URL when attempting to extract UUID")

    # Try UUID format first (with dashes)
    match = UUID_RE.search(url)
    if match:
        return match.group(1)

    # Fall back to hex ID format (without dashes)
    match = HEX_ID_RE.search(url)
    if match:
        return match.group(1)

    raise ValueError(f"Could not extract id from URL: {url}")


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text or text == "--":
        return None
    return text


def slugify(label: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", label.lower())
    return normalized.strip("_")


def parse_date(value: str | None) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    for fmt in ("%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return text


def parse_fighter_list_row(row: Selector) -> dict[str, Any] | None:
    # Try multiple selectors to find the fighter detail URL
    detail_url = (
        clean_text(row.css("td:nth-child(1) a::attr(href)").get()) or
        clean_text(row.css("td:first-child a::attr(href)").get()) or
        clean_text(row.css("a[href*='fighter-details']::attr(href)").get())
    )

    if not detail_url:
        # Log the row HTML for debugging
        row_html = row.get()
        logger.warning(f"No fighter URL found in row. Row HTML: {row_html[:500]}")
        return None

    try:
        fighter_id = _extract_uuid(detail_url)
    except ValueError as e:
        logger.warning(f"Failed to extract UUID from URL '{detail_url}': {e}")
        return None

    data = {
        "item_type": "fighter_list",
        "fighter_id": fighter_id,
        "detail_url": detail_url,
        "name": clean_text(row.css("td:nth-child(1) a::text").get()) or fighter_id,
        "nickname": clean_text(row.css("td:nth-child(1) span.b-statistics__nickname::text").get()),
        "height": clean_text(row.css("td:nth-child(2) p::text").get()),
        "weight": clean_text(row.css("td:nth-child(3) p::text").get()),
        "reach": clean_text(row.css("td:nth-child(4) p::text").get()),
        "stance": clean_text(row.css("td:nth-child(5) p::text").get()),
        "dob": parse_date(row.css("td:nth-child(6) p::text").get()),
    }
    return data


def parse_stat_section(section: Selector) -> dict[str, Any]:
    stats: dict[str, Any] = {}
    for row in section.css("li"):
        label = clean_text(row.css("i::text").get())
        if not label:
            label = clean_text(row.css("span.b-list__info-box-title::text").get())
        if not label:
            continue
        value_candidates: Iterable[str | None] = row.css("strong::text").getall() or row.css(
            "span::text"
        ).getall()
        if not value_candidates:
            value_candidates = row.css("::text").getall()
        value = next((clean_text(val) for val in value_candidates if clean_text(val)), None)
        stats[slugify(label.replace(":", ""))] = value
    return stats


def parse_fight_history_rows(fighter_id: str, table: Selector) -> list[dict[str, Any]]:
    fights = []
    rows = table.css("tbody tr")
    if not rows:
        rows = table.css("tr.b-fight-details__table-row")
    for index, row in enumerate(rows, start=1):
        fight_link = row.css("td:nth-child(1) a::attr(href)").get()
        fight_id = (
            _extract_uuid(fight_link)
            if fight_link
            else f"{fighter_id}-fight-{index}"
        )
        opponent_link = row.css("td:nth-child(2) a::attr(href)").get()
        event_cell = row.css("td:nth-child(7)")
        fights.append(
            {
                "fight_id": fight_id,
                "opponent": clean_text(row.css("td:nth-child(2) a::text").get())
                or clean_text(row.css("td:nth-child(2)::text").get())
                or "Unknown",
                "opponent_id": _extract_uuid(opponent_link) if opponent_link else None,
                "event_name": clean_text(event_cell.css("a::text").get())
                or clean_text(event_cell.css("::text").get()),
                "event_date": parse_date(event_cell.css("span::text").get()),
                "result": clean_text(row.css("td:nth-child(1)::text").get()),
                "method": clean_text(row.css("td:nth-child(8)::text").get()),
                "round": _parse_int(row.css("td:nth-child(9)::text").get()),
                "time": clean_text(row.css("td:nth-child(10)::text").get()),
                "fight_card_url": clean_text(event_cell.css("a::attr(href)").get()),
                "stats": {
                    "sig_strikes": clean_text(row.css("td:nth-child(3)::text").get()),
                    "sig_strikes_pct": clean_text(row.css("td:nth-child(4)::text").get()),
                    "total_strikes": clean_text(row.css("td:nth-child(5)::text").get()),
                    "takedowns": clean_text(row.css("td:nth-child(6)::text").get()),
                },
            }
        )
    return fights


def _parse_int(value: str | None) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_fighter_detail_page(response) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    selector = response if hasattr(response, "css") else Selector(text=response)
    fighter_id = _extract_uuid(getattr(response, "url", None))

    hero = selector.css("div.b-content__banner") or selector.css("div.b-content__title")
    name = clean_text(hero.css("span.b-content__title-highlight::text").get()) or fighter_id
    nickname = clean_text(hero.css("span.b-content__Nickname::text").get())
    record_text = clean_text(hero.css("span.b-content__title-record::text").get())
    record = record_text.split(":")[-1].strip() if record_text and ":" in record_text else record_text

    bio_map: dict[str, str | None] = {}
    for row in selector.css("ul.b-list__box-list li"):
        label = clean_text(row.css("i::text").get())
        if not label:
            continue
        label = label.replace(":", "")
        value_candidates = row.css("span::text, strong::text, ::text").getall()
        value = next(
            (
                clean_text(candidate)
                for candidate in value_candidates
                if clean_text(candidate) and clean_text(candidate) != f"{label}:"
            ),
            None,
        )
        bio_map[label.upper()] = value

    stat_sections = {}
    for section in selector.css("section.b-list__info-box"):
        title = clean_text(section.css("h2::text, h3::text").get()) or "stats"
        stat_sections[slugify(title)] = parse_stat_section(section)

    fight_history_table = selector.css("table.b-fight-details__table")
    fight_history = parse_fight_history_rows(fighter_id, fight_history_table) if fight_history_table else []

    detail = {
        "item_type": "fighter_detail",
        "fighter_id": fighter_id,
        "detail_url": getattr(response, "url", None),
        "name": name,
        "nickname": nickname,
        "record": record,
        "height": bio_map.get("HEIGHT"),
        "weight": bio_map.get("WEIGHT"),
        "reach": bio_map.get("REACH"),
        "leg_reach": bio_map.get("LEG REACH"),
        "stance": bio_map.get("STANCE"),
        "age": _parse_int(bio_map.get("AGE")),
        "dob": parse_date(bio_map.get("DOB")),
        "division": clean_text(selector.css("div.b-fight-details__person i::text").get()),
        "striking": stat_sections.get("striking", {}) or stat_sections.get("strikes", {}),
        "grappling": stat_sections.get("grappling", {}) or stat_sections.get("grappling_totals", {}),
        "significant_strikes": stat_sections.get("significant_strikes", {}),
        "takedown_stats": stat_sections.get("takedowns", {}) or stat_sections.get("grappling", {}),
        "fight_history": fight_history,
    }
    return detail

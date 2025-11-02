from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Iterable

from parsel import Selector

from scraper.utils.weight_classes import weight_to_division

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
    # Remove periods after month abbreviations (e.g., "Nov. 16, 2024" -> "Nov 16, 2024")
    text_normalized = text.replace(".", "")
    for fmt in ("%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text_normalized, fmt).date().isoformat()
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

    # Extract first name (column 1) and last name (column 2)
    first_name = clean_text(row.css("td:nth-child(1) a::text").get())
    last_name = clean_text(row.css("td:nth-child(2) a::text").get())

    # Combine first and last name
    name_parts = [first_name, last_name]
    fighter_name = " ".join(filter(None, name_parts)) or fighter_id

    nickname = clean_text(row.css(".b-statistics__nickname::text").get()) or clean_text(
        row.css("td:nth-child(3) a::text").get()
    )
    height = clean_text(row.css("td:nth-child(2)::text").get()) or clean_text(
        row.css("td:nth-child(2) ::text").get()
    )
    weight = clean_text(row.css("td:nth-child(3)::text").get()) or clean_text(
        row.css("td:nth-child(3) ::text").get()
    )
    reach = clean_text(row.css("td:nth-child(4)::text").get()) or clean_text(
        row.css("td:nth-child(4) ::text").get()
    )
    stance = clean_text(row.css("td:nth-child(5)::text").get()) or clean_text(
        row.css("td:nth-child(5) ::text").get()
    )
    dob_text = clean_text(row.css("td:nth-child(6)::text").get()) or clean_text(
        row.css("td:nth-child(6) ::text").get()
    )
    dob = parse_date(dob_text) if dob_text else None

    data = {
        "item_type": "fighter_list",
        "fighter_id": fighter_id,
        "detail_url": detail_url,
        "name": fighter_name,
        "nickname": nickname,
        "height": height,
        "weight": weight,
        "reach": reach,
        "stance": stance,
        "dob": dob,
        "division": weight_to_division(weight),
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
    def _extract_fighter_stat(cell: Selector | None) -> str | None:
        """Extract only the fighter's stat (first value), not the opponent's."""
        if not cell:
            return None
        # Each cell has two <p> elements: fighter's stat and opponent's stat
        # We only want the first one (the fighter's stat)
        first_p = cell.css("p.b-fight-details__table-text::text").get()
        return clean_text(first_p)

    def _extract_opponent_name(fighter_cell: Selector) -> str:
        """Extract opponent name (second fighter in the cell).

        UFCStats.com shows BOTH fighters in column 2:
        - First link: the page owner (e.g., "Jon Jones")
        - Second link: the opponent (e.g., "Stipe Miocic")
        """
        fighter_links = fighter_cell.css("p.b-fight-details__table-text a::text").getall()
        if len(fighter_links) >= 2:
            return clean_text(fighter_links[1]) or "Unknown"
        # Fallback for cases with only one fighter listed
        return clean_text(fighter_links[0]) if fighter_links else "Unknown"

    def _extract_opponent_id(fighter_cell: Selector) -> str | None:
        """Extract opponent ID (second link in the cell)."""
        opponent_links = fighter_cell.css("p.b-fight-details__table-text a::attr(href)").getall()
        if len(opponent_links) >= 2:
            try:
                return _extract_uuid(opponent_links[1])
            except ValueError:
                return None
        return None

    def _extract_event_date(event_cell: Selector) -> str | None:
        """Extract event date from second <p> tag in event cell."""
        # Date is in the second <p> tag after the flag icon
        date_texts = event_cell.css("p:nth-child(2)::text").getall()
        # Filter out whitespace and join remaining text
        cleaned_parts = [clean_text(t) for t in date_texts if clean_text(t)]
        date_str = " ".join(cleaned_parts) if cleaned_parts else None
        return parse_date(date_str)

    fights = []
    rows = table.css("tbody tr")
    if not rows:
        rows = table.css("tr.b-fight-details__table-row")

    for index, row in enumerate(rows, start=1):
        # Skip empty rows (first row in tbody is often empty with class "b-statistics__table-col_type_clear")
        if row.css("td.b-fight-details__table-col_type_clear"):
            continue

        fight_link = row.css("td:nth-child(1) a::attr(href)").get()
        fight_id = (
            _extract_uuid(fight_link)
            if fight_link
            else f"{fighter_id}-fight-{index}"
        )

        fighter_cell = row.css("td:nth-child(2)")
        event_cell = row.css("td:nth-child(7)")

        # Actual column mapping from UFCStats.com:
        # Col 3: Kd (knockdowns), Col 4: Str (strikes), Col 5: Td (takedowns), Col 6: Sub (submissions)
        knockdowns_cell = row.css("td:nth-child(3)")
        strikes_cell = row.css("td:nth-child(4)")
        takedowns_cell = row.css("td:nth-child(5)")
        submissions_cell = row.css("td:nth-child(6)")

        fights.append(
            {
                "fight_id": fight_id,
                "opponent": _extract_opponent_name(fighter_cell),
                "opponent_id": _extract_opponent_id(fighter_cell),
                "event_name": clean_text(event_cell.css("a::text").get())
                or clean_text(event_cell.css("p:nth-child(1)::text").get()),
                "event_date": _extract_event_date(event_cell),
                "result": clean_text(row.css("td:nth-child(1) a i.b-flag__text::text").get()),
                "method": " ".join([clean_text(t) for t in row.css("td:nth-child(8) p:nth-child(1)::text").getall() if clean_text(t)]) or None,
                "round": _parse_int(row.css("td:nth-child(9) p::text").get()),
                "time": clean_text(row.css("td:nth-child(10) p::text").get()),
                "fight_card_url": clean_text(event_cell.css("a::attr(href)").get()),
                "stats": {
                    "knockdowns": _extract_fighter_stat(knockdowns_cell),
                    "total_strikes": _extract_fighter_stat(strikes_cell),
                    "takedowns": _extract_fighter_stat(takedowns_cell),
                    "submissions": _extract_fighter_stat(submissions_cell),
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

    hero = selector.css(".b-content__banner") or selector.css(".b-content__title")

    # Try multiple selectors for fighter name with fallbacks
    name_candidates = (
        hero.css("span.b-content__title-highlight::text").getall()
        or selector.css("h2.b-content__title span.b-content__title-highlight::text").getall()
        or selector.css(".b-content__title-highlight::text").getall()
        or hero.css("h2::text").getall()
    )
    # Join all text parts and clean
    full_name = " ".join(filter(None, (clean_text(n) for n in name_candidates if n)))
    name = full_name.strip() if full_name else fighter_id

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

    weight = bio_map.get("WEIGHT")
    scraped_division = clean_text(selector.css("div.b-fight-details__person i::text").get())

    detail = {
        "item_type": "fighter_detail",
        "fighter_id": fighter_id,
        "detail_url": getattr(response, "url", None),
        "name": name,
        "nickname": nickname,
        "record": record,
        "height": bio_map.get("HEIGHT"),
        "weight": weight,
        "reach": bio_map.get("REACH"),
        "leg_reach": bio_map.get("LEG REACH"),
        "stance": bio_map.get("STANCE"),
        "age": _parse_int(bio_map.get("AGE")),
        "dob": parse_date(bio_map.get("DOB")),
        "division": scraped_division or weight_to_division(weight),
        "striking": stat_sections.get("striking", {}) or stat_sections.get("strikes", {}),
        "grappling": stat_sections.get("grappling", {}) or stat_sections.get("grappling_totals", {}),
        "significant_strikes": stat_sections.get("significant_strikes", {}),
        "takedown_stats": stat_sections.get("takedowns", {}) or stat_sections.get("grappling", {}),
        "fight_history": fight_history,
    }
    return detail

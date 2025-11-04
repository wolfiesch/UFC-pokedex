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
    # Try multiple date formats
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):  # %B = full month name, %b = abbreviated
        try:
            return datetime.strptime(text_normalized, fmt).date().isoformat()
        except ValueError:
            continue
    return text


def parse_fighter_list_row(row: Selector) -> dict[str, Any] | None:
    # Try multiple selectors to find the fighter detail URL
    detail_url = (
        clean_text(row.css("td:nth-child(1) a::attr(href)").get())
        or clean_text(row.css("td:first-child a::attr(href)").get())
        or clean_text(row.css("a[href*='fighter-details']::attr(href)").get())
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
    """Normalise statistics blocks found on fighter detail pages.

    The UFCStats markup has evolved from <section> + <li> structures to nested
    <div> blocks containing ``.b-list__box-list-item`` rows. This helper walks
    any combination of ``li`` or ``div`` rows and extracts the first clean value
    that does not simply repeat the label text.
    """

    stats: dict[str, Any] = {}
    # Stats are nested inside <ul class="b-list__box-list"> within the section
    rows = section.css("ul.b-list__box-list li, .b-list__box-list-item")

    for row in rows:
        label_candidates = row.css(
            "i::text, span.b-list__info-box-title::text, p.b-list__info-box-title::text"
        )
        label = next(
            (
                clean_text(text)
                for text in label_candidates.getall()
                if clean_text(text)
            ),
            None,
        )
        if not label:
            continue

        normalized_label = label.replace(":", "")

        value = None
        for raw_value in row.css("strong::text, span::text, ::text").getall():
            cleaned = clean_text(raw_value)
            if not cleaned:
                continue
            if cleaned == label or cleaned == normalized_label:
                continue
            value = cleaned
            break

        if value is None:
            continue

        stats[slugify(normalized_label)] = value

    return stats


def parse_fight_history_rows(fighter_id: str, table: Selector) -> list[dict[str, Any]]:
    def _extract_fighter_stat(cell: Selector | None) -> str | None:
        """Extract only the fighter's stat (first value), not the opponent's."""
        if not cell:
            return None
        # Each cell has two <p> elements: fighter's stat and opponent's stat
        # We only want the first one (the fighter's stat)
        stat_candidates: list[str] = cell.css(
            "p.b-fight-details__table-text::text, p::text, ::text"
        ).getall()
        for candidate in stat_candidates:
            cleaned = clean_text(candidate)
            if cleaned:
                return cleaned
        return None

    def _extract_opponent_name(fighter_cell: Selector) -> str:
        """Extract opponent name (second fighter in the cell).

        UFCStats.com shows BOTH fighters in column 2:
        - First link: the page owner (e.g., "Jon Jones")
        - Second link: the opponent (e.g., "Stipe Miocic")
        """
        fighter_links: list[str] = fighter_cell.css(
            "p.b-fight-details__table-text a::text"
        ).getall()
        if not fighter_links:
            # Some archived event pages omit the ``b-fight-details__table-text``
            # class, so we gracefully fall back to any anchor tags inside the
            # cell.
            fighter_links = fighter_cell.css("a::text").getall()
        if len(fighter_links) >= 2:
            return clean_text(fighter_links[1]) or "Unknown"
        # Fallback for cases with only one fighter listed
        return clean_text(fighter_links[0]) if fighter_links else "Unknown"

    def _extract_opponent_id(fighter_cell: Selector) -> str | None:
        """Extract opponent ID (second link in the cell)."""
        opponent_links: list[str] = fighter_cell.css(
            "p.b-fight-details__table-text a::attr(href)"
        ).getall()
        if not opponent_links:
            # Same fallback logic as ``_extract_opponent_name`` for legacy
            # markup without the class attribute.
            opponent_links = fighter_cell.css("a::attr(href)").getall()
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

    def _extract_result(cell: Selector) -> str | None:
        """Retrieve the fight result (e.g., ``W``/``L``) regardless of markup."""

        result_candidates: list[str | None] = [
            cell.css("a i.b-flag__text::text").get(),
            cell.css("a::text").get(),
            cell.css("::text").get(),
        ]

        for candidate in result_candidates:
            cleaned = clean_text(candidate)
            if cleaned:
                return cleaned
        return None

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
            _extract_uuid(fight_link) if fight_link else f"{fighter_id}-fight-{index}"
        )

        fighter_cell = row.css("td:nth-child(2)")
        event_cell = row.css("td:nth-child(7)")

        # Actual column mapping from UFCStats.com:
        # Col 3: Kd (knockdowns), Col 4: Str (strikes), Col 5: Td (takedowns), Col 6: Sub (submissions)
        knockdowns_cell = row.css("td:nth-child(3)")
        strikes_cell = row.css("td:nth-child(4)")
        takedowns_cell = row.css("td:nth-child(5)")
        submissions_cell = row.css("td:nth-child(6)")

        opponent_name = _extract_opponent_name(fighter_cell)
        event_name = clean_text(event_cell.css("a::text").get()) or clean_text(
            event_cell.css("p:nth-child(1)::text").get()
        )
        result = _extract_result(row.css("td:nth-child(1)"))
        event_date = _extract_event_date(event_cell)

        # Skip placeholder fights: rows where ALL key fields are None/Unknown
        # These are empty table rows that UFCStats includes for formatting
        if (
            (opponent_name in (None, "Unknown"))
            and event_name is None
            and result is None
            and event_date is None
        ):
            continue

        fights.append(
            {
                "fight_id": fight_id,
                "opponent": opponent_name,
                "opponent_id": _extract_opponent_id(fighter_cell),
                "event_name": event_name,
                "event_date": event_date,
                "result": result,
                "method": " ".join(
                    [
                        clean_text(t)
                        for t in row.css(
                            "td:nth-child(8) p:nth-child(1)::text"
                        ).getall()
                        if clean_text(t)
                    ]
                )
                or None,
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

    # Try multiple selectors for fighter name with fallbacks
    name_candidates = (
        selector.css("h2.b-content__title span.b-content__title-highlight::text").getall()
        or selector.css(".b-content__title-highlight::text").getall()
        or selector.css(".b-content__banner h2::text").getall()
        or selector.css(".b-content__title h2::text").getall()
    )
    # Join all text parts and clean
    full_name = " ".join(filter(None, (clean_text(n) for n in name_candidates if n)))
    name = full_name.strip() if full_name else fighter_id

    # Nickname is a <p> tag at the root level, not nested in hero section
    nickname = clean_text(selector.css("p.b-content__Nickname::text").get())
    # Record is in the title heading
    record_text = clean_text(selector.css("span.b-content__title-record::text").get())
    record = (
        record_text.split(":")[-1].strip()
        if record_text and ":" in record_text
        else record_text
    )

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

    stat_sections: dict[str, dict[str, Any]] = {}
    stat_containers = selector.css("section.b-list__info-box, div.b-list__info-box")

    for section in stat_containers:
        title = (
            clean_text(
                section.css("h2::text, h3::text, i.b-list__box-item-title::text").get()
            )
            or "stats"
        )
        title = title.replace(":", "")
        parsed_section = parse_stat_section(section)
        if not parsed_section:
            continue
        key = slugify(title)
        existing = stat_sections.setdefault(key, {})
        existing.update(parsed_section)

    fight_history_table = selector.css("table.b-fight-details__table")
    fight_history = (
        parse_fight_history_rows(fighter_id, fight_history_table)
        if fight_history_table
        else []
    )

    weight = bio_map.get("WEIGHT")
    scraped_division = clean_text(
        selector.css("div.b-fight-details__person i::text").get()
    )

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
        "striking": (
            stat_sections.get("striking", {})
            or stat_sections.get("strikes", {})
            or stat_sections.get("career_statistics", {})
            or {}
        ),
        "grappling": (
            stat_sections.get("grappling", {})
            or stat_sections.get("grappling_totals", {})
            or stat_sections.get("career_statistics", {})
            or {}
        ),
        "significant_strikes": stat_sections.get("significant_strikes", {}) or stat_sections.get("career_statistics", {}),
        "takedown_stats": stat_sections.get("takedowns", {})
        or stat_sections.get("grappling", {})
        or stat_sections.get("career_statistics", {}),
        "fight_history": fight_history,
    }
    return detail


def parse_events_list_row(row: Selector) -> dict[str, Any] | None:
    """Parse a single row from the UFCStats events list table."""
    # Event detail URL is in first column
    detail_url = clean_text(row.css("td:nth-child(1) a::attr(href)").get())

    if not detail_url:
        return None

    try:
        event_id = _extract_uuid(detail_url)
    except ValueError as e:
        logger.warning(f"Failed to extract ID from URL '{detail_url}': {e}")
        return None

    # Event name (link text in column 1)
    event_name = clean_text(row.css("td:nth-child(1) a::text").get())

    # Event date (second element in column 1, after the link)
    # The date is in a span/div after the link
    date_text = None
    # Try to get all text from first column and find the date
    all_text_col1 = row.css("td:nth-child(1) ::text").getall()
    for text in all_text_col1:
        cleaned = clean_text(text)
        if cleaned and cleaned != event_name:
            # This should be the date
            date_text = cleaned
            break

    event_date = parse_date(date_text) if date_text else None

    # Location (column 2)
    location = clean_text(row.css("td:nth-child(2)::text").get())

    # Determine status based on context (caller should pass this)
    # For now, we'll determine it based on the date
    from datetime import datetime, date as date_type
    status = "upcoming"
    if event_date:
        try:
            parsed_date = datetime.fromisoformat(event_date).date()
            if parsed_date <= datetime.now().date():
                status = "completed"
        except (ValueError, AttributeError):
            pass

    return {
        "item_type": "event_list",
        "event_id": event_id,
        "detail_url": detail_url,
        "name": event_name,
        "date": event_date,
        "location": location,
        "status": status,
    }


def parse_event_detail_page(response) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """Parse an event detail page from UFCStats."""
    selector = response if hasattr(response, "css") else Selector(text=response)
    event_url = getattr(response, "url", None)

    try:
        event_id = _extract_uuid(event_url)
    except ValueError:
        logger.error(f"Could not extract event ID from URL: {event_url}")
        raise

    # Event name from header
    event_name = clean_text(
        selector.css("h2.b-content__title span.b-content__title-highlight::text").get()
    )

    # Event metadata from list items
    metadata_map: dict[str, str | None] = {}
    for row in selector.css("ul.b-list__box-list li"):
        label_text = clean_text(row.css("i::text").get())
        if not label_text:
            continue

        # Store label for comparison (before modification)
        original_label = label_text
        label = label_text.replace(":", "").upper()

        # Get all text and filter out the label itself (case-insensitive)
        all_text = row.css("::text").getall()
        value = next(
            (
                clean_text(t)
                for t in all_text
                if clean_text(t) and clean_text(t).upper() != f"{label}:" and clean_text(t) != original_label
            ),
            None,
        )
        metadata_map[label] = value

    # Parse date and location
    event_date = parse_date(metadata_map.get("DATE"))
    location = metadata_map.get("LOCATION")

    # Determine status
    from datetime import datetime
    status = "upcoming"
    if event_date:
        try:
            parsed_date = datetime.fromisoformat(event_date).date()
            if parsed_date <= datetime.now().date():
                status = "completed"
        except (ValueError, AttributeError):
            pass

    # Parse fight card table
    fight_card = []
    fight_table = selector.css("table.b-fight-details__table")

    if fight_table:
        rows = fight_table.css("tbody tr")
        for index, row in enumerate(rows, start=1):
            # Skip empty rows
            if row.css("td.b-fight-details__table-col_type_clear"):
                continue

            # Fight URL (column 1)
            fight_url = clean_text(row.css("td:nth-child(1)::attr(onclick)").get())
            if fight_url:
                # Extract URL from onclick="doNav('url')"
                import re
                match = re.search(r"doNav\('([^']+)'\)", fight_url)
                if match:
                    fight_url = match.group(1)

            fight_id = None
            if fight_url:
                try:
                    fight_id = _extract_uuid(fight_url)
                except ValueError:
                    pass

            # Fighter names (column 2) - contains two links
            fighter_links = row.css("td:nth-child(2) p a")
            fighter_1_name = clean_text(fighter_links[0].css("::text").get()) if len(fighter_links) > 0 else None
            fighter_2_name = clean_text(fighter_links[1].css("::text").get()) if len(fighter_links) > 1 else None

            # Fighter IDs
            fighter_urls = row.css("td:nth-child(2) p a::attr(href)").getall()
            fighter_1_id = None
            fighter_2_id = None
            if len(fighter_urls) > 0:
                try:
                    fighter_1_id = _extract_uuid(fighter_urls[0])
                except ValueError:
                    pass
            if len(fighter_urls) > 1:
                try:
                    fighter_2_id = _extract_uuid(fighter_urls[1])
                except ValueError:
                    pass

            # Weight class (column 6 in the table - the 7th column because of how they count)
            weight_class = clean_text(row.css("td:nth-child(7) p::text").get())

            # Result fields (for completed events)
            # Column 8: Method, Column 9: Round, Column 10: Time
            method = " ".join([
                clean_text(t) for t in row.css("td:nth-child(8) p::text").getall()
                if clean_text(t)
            ]) or None
            round_num = _parse_int(row.css("td:nth-child(9) p::text").get())
            time = clean_text(row.css("td:nth-child(10) p::text").get())

            # Stats (columns 3-6): Kd, Str, Td, Sub
            stats = {
                "knockdowns": clean_text(row.css("td:nth-child(3) p::text").get()),
                "strikes": clean_text(row.css("td:nth-child(4) p::text").get()),
                "takedowns": clean_text(row.css("td:nth-child(5) p::text").get()),
                "submissions": clean_text(row.css("td:nth-child(6) p::text").get()),
            }

            # Skip if we don't have at least fighter names
            if not fighter_1_name or not fighter_2_name:
                continue

            fight_card.append({
                "fight_id": fight_id or f"{event_id}-fight-{index}",
                "fighter_1_id": fighter_1_id,
                "fighter_1_name": fighter_1_name,
                "fighter_2_id": fighter_2_id,
                "fighter_2_name": fighter_2_name,
                "weight_class": weight_class,
                "result": None,  # Need to determine from fight detail page
                "method": method,
                "round": round_num,
                "time": time,
                "fight_url": fight_url,
                "stats": stats,
            })

    return {
        "item_type": "event_detail",
        "event_id": event_id,
        "detail_url": event_url,
        "name": event_name,
        "date": event_date,
        "location": location,
        "status": status,
        "venue": None,  # Not available on UFCStats
        "promotion": "UFC",
        "fight_card": fight_card,
    }


def parse_tapology_event(response, ufcstats_event_id: str) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """Parse Tapology event page for enrichment data."""
    selector = response if hasattr(response, "css") else Selector(text=response)
    tapology_url = getattr(response, "url", None)

    # Venue information
    venue = clean_text(selector.css(".eventPageHeaderTitles .subtitle::text").get())

    # Broadcast information (look for ESPN+, PPV, etc.)
    broadcast = clean_text(selector.css(".billing::text").get())

    # Cross-references
    sherdog_url = None
    for link in selector.css("a[href*='sherdog.com']::attr(href)").getall():
        sherdog_url = clean_text(link)
        break

    # Fighter rankings (from fight card)
    fighter_rankings: dict[str, str] = {}
    for bout in selector.css(".fightCard li.boutCard"):
        # Extract fighter names and rankings
        for fighter in bout.css(".fighterName"):
            name = clean_text(fighter.css("a::text").get())
            ranking = clean_text(fighter.css(".ranking::text").get())
            if name and ranking:
                # We'll need to match this to fighter IDs later in the spider
                fighter_rankings[name] = ranking

    return {
        "item_type": "tapology_enrichment",
        "event_id": ufcstats_event_id,
        "tapology_url": tapology_url,
        "sherdog_url": sherdog_url,
        "venue": venue,
        "broadcast": broadcast,
        "fighter_rankings": fighter_rankings,
    }

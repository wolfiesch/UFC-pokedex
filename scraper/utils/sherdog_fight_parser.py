"""Parser for Sherdog fight history tables.

This module extracts complete fight records from Sherdog fighter profile pages.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from parsel import Selector

logger = logging.getLogger(__name__)


def clean_text(value: str | None) -> str | None:
    """Clean and normalize text value.

    Args:
        value: Raw text from HTML

    Returns:
        Cleaned text or None if empty/missing
    """
    if value is None:
        return None
    text = value.strip()
    if not text or text in ("--", "N/A", "n/a"):
        return None
    return text


def parse_sherdog_date(date_str: str | None) -> str | None:
    """Parse Sherdog fight date to ISO format (YYYY-MM-DD).

    Sherdog uses format: "Nov / 26 / 2022" or "November 26, 2022"

    Args:
        date_str: Date string from Sherdog

    Returns:
        ISO formatted date (YYYY-MM-DD) or None
    """
    text = clean_text(date_str)
    if not text:
        return None

    # Remove extra whitespace around slashes
    text = re.sub(r"\s*/\s*", "/", text)

    # Try multiple date formats
    formats = [
        "%b/%d/%Y",  # Nov/26/2022
        "%B/%d/%Y",  # November/26/2022
        "%b %d, %Y",  # Nov 26, 2022
        "%B %d, %Y",  # November 26, 2022
        "%Y-%m-%d",  # 2022-11-26
        "%m/%d/%Y",  # 11/26/2022
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue

    logger.warning(f"Could not parse fight date: {text}")
    return None


def parse_fight_result(result_elem) -> str | None:
    """Parse fight result (Win/Loss/Draw/NC).

    Args:
        result_elem: Selector for result element

    Returns:
        Normalized result string or None
    """
    if not result_elem:
        return None

    # Result is in span with class like "final_result win"
    result_span = result_elem.css("span.final_result::text").get()
    if result_span:
        result = clean_text(result_span)
        if result:
            # Normalize to uppercase
            result = result.upper()
            # Map common variations
            result_map = {
                "WIN": "Win",
                "LOSS": "Loss",
                "DRAW": "Draw",
                "NC": "NC",
                "NO CONTEST": "NC",
            }
            return result_map.get(result, result.capitalize())

    return None


def parse_opponent(opponent_elem) -> dict[str, Any]:
    """Parse opponent information.

    Args:
        opponent_elem: Selector for opponent cell

    Returns:
        Dict with opponent_name and opponent_sherdog_id
    """
    if not opponent_elem:
        return {"opponent_name": None, "opponent_sherdog_id": None}

    # Opponent link: <a href="/fighter/Name-ID">Name</a>
    opponent_link = opponent_elem.css("a")
    if not opponent_link:
        # Sometimes just text
        text = clean_text(opponent_elem.css("::text").get())
        return {"opponent_name": text, "opponent_sherdog_id": None}

    opponent_name = clean_text(opponent_link.css("::text").get())
    opponent_url = opponent_link.css("::attr(href)").get()

    # Extract Sherdog ID from URL: /fighter/Name-12345 -> 12345
    opponent_id = None
    if opponent_url:
        parts = opponent_url.rstrip("/").split("-")
        if parts:
            try:
                opponent_id = int(parts[-1])
            except ValueError:
                pass

    return {
        "opponent_name": opponent_name,
        "opponent_sherdog_id": opponent_id,
    }


def parse_event(event_elem) -> dict[str, Any]:
    """Parse event information.

    Args:
        event_elem: Selector for event cell

    Returns:
        Dict with event_name, event_sherdog_id, event_date, promotion
    """
    if not event_elem:
        return {
            "event_name": None,
            "event_sherdog_id": None,
            "event_date": None,
            "promotion": None,
        }

    # Event link: <a href="/events/..."><span>Event Name</span></a>
    event_link = event_elem.css("a")
    event_name = None
    event_id = None
    promotion = None

    if event_link:
        # Try to get event name from span with itemprop="award"
        event_name = clean_text(event_link.css("span[itemprop='award']::text").get())
        if not event_name:
            # Fallback to link text
            event_name = clean_text(event_link.css("::text").get())

        # Extract event ID from URL
        event_url = event_link.css("::attr(href)").get()
        if event_url:
            # URL format: /events/Promotion-Event-Name-12345
            parts = event_url.rstrip("/").split("-")
            if parts:
                try:
                    event_id = int(parts[-1])
                except ValueError:
                    pass

            # Try to extract promotion from event name
            # Common formats: "UFC 300", "Bellator 301", "PFL 2023"
            if event_name:
                promotion_match = re.match(r"^([A-Z]+(?:\s+[A-Z]+)?)\s*[-:]?\s*", event_name)
                if promotion_match:
                    promotion = promotion_match.group(1).strip()

    # Parse date from sub_line
    date_str = clean_text(event_elem.css("span.sub_line::text").get())
    event_date = parse_sherdog_date(date_str)

    return {
        "event_name": event_name,
        "event_sherdog_id": event_id,
        "event_date": event_date,
        "promotion": promotion,
    }


def parse_method(method_elem) -> dict[str, Any]:
    """Parse fight finish method.

    Args:
        method_elem: Selector for method cell

    Returns:
        Dict with method, method_details
    """
    if not method_elem:
        return {"method": None, "method_details": None}

    # Method is in <b> tag, details in sub_line
    method = clean_text(method_elem.css("b::text").get())
    method_details = clean_text(method_elem.css("span.sub_line::text").get())

    return {
        "method": method,
        "method_details": method_details,
    }


def parse_sherdog_fight_history(
    response: Selector, fighter_sherdog_id: int | None = None
) -> list[dict[str, Any]]:
    """Parse complete fight history from Sherdog fighter page.

    Args:
        response: Scrapy response selector
        fighter_sherdog_id: Sherdog ID of the fighter (for context)

    Returns:
        List of fight records, each as a dict with:
            - result: Win/Loss/Draw/NC
            - opponent_name: Fighter name
            - opponent_sherdog_id: Opponent's Sherdog ID
            - event_name: Event name
            - event_sherdog_id: Event ID
            - event_date: Fight date (ISO format)
            - promotion: Organization/promotion
            - method: Finish method
            - method_details: Additional method info
            - round: Round number
            - time: Time in round (M:SS)
    """
    fights = []

    # Find fight history table
    # Sherdog uses: <table class="new_table fighter">
    fight_table = response.css("table.fighter")

    if not fight_table:
        logger.warning("No fight history table found on page")
        return []

    # Get all fight rows (skip header)
    fight_rows = fight_table.css("tr")[1:]  # Skip header row

    logger.info(f"Found {len(fight_rows)} fights in history")

    for row in fight_rows:
        cells = row.css("td")

        if len(cells) < 6:
            logger.warning(f"Skipping row with only {len(cells)} cells")
            continue

        # Parse each component
        result = parse_fight_result(cells[0])
        opponent = parse_opponent(cells[1])
        event = parse_event(cells[2])
        method = parse_method(cells[3])

        # Round and time are simple text
        round_num = clean_text(cells[4].css("::text").get())
        time = clean_text(cells[5].css("::text").get())

        # Convert round to integer if possible
        round_int = None
        if round_num:
            try:
                round_int = int(round_num)
            except ValueError:
                pass

        fight = {
            "result": result,
            "opponent_name": opponent["opponent_name"],
            "opponent_sherdog_id": opponent["opponent_sherdog_id"],
            "event_name": event["event_name"],
            "event_sherdog_id": event["event_sherdog_id"],
            "event_date": event["event_date"],
            "promotion": event["promotion"],
            "method": method["method"],
            "method_details": method["method_details"],
            "round": round_int,
            "time": time,
        }

        fights.append(fight)

    logger.info(f"Successfully parsed {len(fights)} fights")

    return fights

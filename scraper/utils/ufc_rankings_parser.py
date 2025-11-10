"""Parser utilities for UFC.com rankings pages.

This module provides functions to parse HTML from UFC.com rankings pages
and extract fighter ranking data organized by weight class.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from parsel import Selector


def parse_ufc_rankings_page(html: str, rank_date: date | None = None) -> list[dict[str, Any]]:
    """Parse UFC.com rankings page and extract all rankings by division.

    Args:
        html: Raw HTML from UFC.com rankings page
        rank_date: Date of ranking snapshot (defaults to today)

    Returns:
        List of ranking dicts with keys:
            - fighter_name: Fighter name
            - division: Weight class
            - rank: Rank position (0=Champion, 1-15)
            - previous_rank: Previous rank (if available)
            - is_interim: Whether interim champion
            - rank_date: Date of ranking
            - source: "ufc"
    """
    selector = Selector(text=html)
    rank_date = rank_date or date.today()

    # Try modern table layout first, fall back to legacy layout if we find nothing.
    rankings = _parse_table_layout(selector, rank_date)
    if rankings:
        return rankings

    return _parse_legacy_layout(selector, rank_date)


def _parse_table_layout(selector: Selector, rank_date: date) -> list[dict[str, Any]]:
    """Parse the modern UFC rankings table layout."""
    rankings: list[dict[str, Any]] = []
    division_sections = selector.css(".view-grouping")

    for section in division_sections:
        division_name_raw = section.css(".view-grouping-header::text").get()
        if not division_name_raw:
            continue

        division_name = normalize_division_name(division_name_raw)
        if "pound" in division_name.lower():
            continue

        champion_block = section.css(".rankings--athlete--champion")
        if champion_block:
            champion_name = champion_block.css(".info a::text").get()
            if champion_name:
                rankings.append({
                    "fighter_name": champion_name.strip(),
                    "division": division_name,
                    "rank": 0,
                    "previous_rank": None,
                    "is_interim": _check_if_interim(champion_block[0]),
                    "rank_date": rank_date,
                    "source": "ufc",
                })

        for row in section.css("tbody tr"):
            rank = _safe_parse_rank(row.css("td:nth-child(1)::text").get())
            fighter_name = row.css("td:nth-child(2) a::text").get()

            if rank is None or not fighter_name:
                continue

            previous_rank = _extract_previous_rank_from_row(row)

            rankings.append({
                "fighter_name": fighter_name.strip(),
                "division": division_name,
                "rank": rank,
                "previous_rank": previous_rank,
                "is_interim": False,
                "rank_date": rank_date,
                "source": "ufc",
            })

    return rankings


def _parse_legacy_layout(selector: Selector, rank_date: date) -> list[dict[str, Any]]:
    """Fallback parser for older layouts (cards/lists)."""
    rankings: list[dict[str, Any]] = []

    division_sections = selector.css(
        ".rankings-list-container, .weight-class-section, .view-grouping"
    )
    if not division_sections:
        division_sections = selector.xpath(
            '//div[contains(@class, "rankings") or contains(@class, "division")]'
        )

    for section in division_sections:
        division_name = (
            section.css("h4::text, h3::text, .weight-class-title::text").get()
            or section.xpath(".//text()[normalize-space()]").get()
        )

        if not division_name:
            continue

        division_name = normalize_division_name(division_name)
        if "pound" in division_name.lower():
            continue

        champion_elem = section.css(".champion, .rankings-athlete-list-item:first-child, .rank-0")
        if champion_elem:
            champion_name = _extract_fighter_name(champion_elem[0])
            if champion_name:
                rankings.append({
                    "fighter_name": champion_name,
                    "division": division_name,
                    "rank": 0,
                    "previous_rank": None,
                    "is_interim": _check_if_interim(champion_elem[0]),
                    "rank_date": rank_date,
                    "source": "ufc",
                })

        ranked_fighters = section.css(".rankings-athlete-list-item, .athlete-item, .fighter-row")
        for fighter_elem in ranked_fighters:
            rank_value = _extract_rank(fighter_elem)
            if rank_value is None:
                continue

            fighter_name = _extract_fighter_name(fighter_elem)
            if not fighter_name:
                continue

            previous_rank = _extract_previous_rank(fighter_elem)

            rankings.append({
                "fighter_name": fighter_name,
                "division": division_name,
                "rank": rank_value,
                "previous_rank": previous_rank,
                "is_interim": False,
                "rank_date": rank_date,
                "source": "ufc",
            })

    return rankings


def _safe_parse_rank(rank_text: str | None) -> int | None:
    """Parse integer rank from raw text."""
    if not rank_text:
        return None
    try:
        value = int(rank_text.strip().replace("#", "").replace(".", ""))
    except ValueError:
        return None
    return value if 0 <= value <= 15 else None


def _extract_fighter_name(fighter_elem: Selector) -> str | None:
    """Extract fighter name from ranking element.

    Tries multiple selectors to handle different HTML structures.

    Args:
        fighter_elem: Parsel selector for fighter element

    Returns:
        Fighter name or None
    """
    # Try multiple selectors
    name = (
        fighter_elem.css('.athlete-name::text').get()
        or fighter_elem.css('.fighter-name::text').get()
        or fighter_elem.css('.name::text').get()
        or fighter_elem.css('a::text').get()
        or fighter_elem.xpath('.//text()[normalize-space()]').get()
    )

    if name:
        return name.strip()

    return None


def _extract_rank(fighter_elem: Selector) -> int | None:
    """Extract rank number from fighter element.

    Args:
        fighter_elem: Parsel selector for fighter element

    Returns:
        Rank as integer (1-15) or None
    """
    rank_text = (
        fighter_elem.css('.rank::text').get()
        or fighter_elem.css('.number::text').get()
        or fighter_elem.css('[class*="rank"]::text').get()
        or fighter_elem.attrib.get('data-rank')
    )

    if not rank_text:
        return None

    rank_text = rank_text.strip().replace("#", "").replace(".", "")

    try:
        rank = int(rank_text)
        if 1 <= rank <= 15:
            return rank
    except ValueError:
        pass

    return None


def _extract_previous_rank(fighter_elem: Selector) -> int | None:
    """Extract previous rank for movement tracking.

    Args:
        fighter_elem: Parsel selector for fighter element

    Returns:
        Previous rank or None
    """
    prev_rank_text = (
        fighter_elem.css('.previous-rank::text').get()
        or fighter_elem.css('[class*="prev"]::text').get()
        or fighter_elem.attrib.get('data-previous-rank')
    )

    if not prev_rank_text:
        return None

    prev_rank_text = prev_rank_text.strip().replace("#", "").replace(".", "")

    try:
        return int(prev_rank_text)
    except ValueError:
        return None


def _check_if_interim(fighter_elem: Selector) -> bool:
    """Check if fighter is interim champion.

    Args:
        fighter_elem: Parsel selector for fighter element

    Returns:
        True if interim champion
    """
    text_content = fighter_elem.get()
    if not text_content:
        return False

    text_content = text_content.lower()
    return "interim" in text_content or "int." in text_content


def _extract_previous_rank_from_row(row: Selector) -> int | None:
    """Extract previous rank from the modern table row."""
    prev_rank_text = (
        row.attrib.get("data-previous-rank")
        or row.css("[data-previous-rank]::attr(data-previous-rank)").get()
    )

    if prev_rank_text:
        try:
            return int(prev_rank_text.strip())
        except ValueError:
            return None

    # Some layouts show movement deltas via data attribute (e.g., data-movement="+1")
    movement_text = row.css("[data-movement]::attr(data-movement)").get()
    rank = _safe_parse_rank(row.css("td:nth-child(1)::text").get())
    if rank is not None and movement_text:
        try:
            movement = int(movement_text.strip())
            return rank + movement * -1  # Movement represents change relative to previous rank
        except ValueError:
            return None

    return None


def normalize_division_name(division: str) -> str:
    """Normalize division name to match database conventions.

    Args:
        division: Raw division name from UFC.com

    Returns:
        Normalized division name
    """
    # Remove common prefixes/suffixes
    normalized = division.strip()
    normalized = normalized.replace("UFC", "").strip()
    normalized = normalized.replace("Division", "").strip()
    normalized = normalized.replace("Class", "").strip()

    # Title case for consistency
    return normalized.title()

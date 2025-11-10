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
    rankings = []

    # UFC.com uses .view-grouping for each division
    division_sections = selector.css('.view-grouping')

    for section in division_sections:
        # Extract division name from header
        division_name_raw = section.css('.view-grouping-header::text').get()

        if not division_name_raw:
            continue

        # Normalize division name for consistent DB storage
        division_name = normalize_division_name(division_name_raw)

        # Skip pound-for-pound rankings (can be added later if needed)
        if "pound" in division_name.lower():
            continue

        # Extract champion
        champion_elem = section.css('.rankings--athlete--champion .info a')
        if champion_elem:
            champion_name = champion_elem.css('::text').get()
            if champion_name:
                champion_name = champion_name.strip()
                # Check for interim in the champion section HTML
                champion_html = section.css('.rankings--athlete--champion').get() or ""
                is_interim = "interim" in champion_html.lower() or "int." in champion_html.lower()

                rankings.append({
                    "fighter_name": champion_name,
                    "division": division_name,
                    "rank": 0,  # Champion = rank 0
                    "previous_rank": None,
                    "is_interim": is_interim,
                    "rank_date": rank_date,
                    "source": "ufc",
                })

        # Extract ranked fighters (1-15) from tbody rows
        for row in section.css('tbody tr'):
            # Rank is in first column
            rank_text = row.css('td:nth-child(1)::text').get()
            # Fighter name is in second column
            fighter_name = row.css('td:nth-child(2) a::text').get()

            if not rank_text or not fighter_name:
                continue

            rank_text = rank_text.strip()
            fighter_name = fighter_name.strip()

            try:
                rank = int(rank_text)
            except ValueError:
                continue

            rankings.append({
                "fighter_name": fighter_name,
                "division": division_name,
                "rank": rank,
                "previous_rank": None,  # UFC.com doesn't show previous rank in current layout
                "is_interim": False,  # Only champion can be interim
                "rank_date": rank_date,
                "source": "ufc",
            })

    return rankings


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

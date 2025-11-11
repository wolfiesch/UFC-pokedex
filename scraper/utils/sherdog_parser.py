"""Utilities for parsing Sherdog fighter profile pages."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from parsel import Selector

from scraper.utils.country_mapping import normalize_nationality

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
    """Parse Sherdog date format to ISO format (YYYY-MM-DD).

    Sherdog typically uses: "YYYY-MM-DD" already, but may also use other formats.

    Args:
        date_str: Date string from Sherdog

    Returns:
        ISO formatted date (YYYY-MM-DD) or None
    """
    text = clean_text(date_str)
    if not text:
        return None

    # Try multiple date formats
    formats = [
        "%Y-%m-%d",  # 2023-01-15
        "%B %d, %Y",  # January 15, 2023
        "%b %d, %Y",  # Jan 15, 2023
        "%m/%d/%Y",  # 01/15/2023
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {text}")
    return text  # Return original if can't parse


def parse_sherdog_height(height_str: str | None) -> dict[str, Any]:
    """Parse Sherdog height to normalized format.

    Sherdog formats:
    - "6' 4\"" (feet and inches)
    - "193 cm" (centimeters)

    Args:
        height_str: Height string from Sherdog

    Returns:
        Dict with 'value' (normalized to ft'in"), 'cm', 'original'
    """
    text = clean_text(height_str)
    if not text:
        return {"value": None, "cm": None, "original": None}

    # Pattern: 6' 4" or 6'4"
    feet_inches_match = re.match(r"(\d+)'?\s*(\d+)\"?", text)
    if feet_inches_match:
        feet = int(feet_inches_match.group(1))
        inches = int(feet_inches_match.group(2))
        # Convert to cm for storage
        total_inches = feet * 12 + inches
        cm = round(total_inches * 2.54, 1)
        return {
            "value": f"{feet}' {inches}\"",
            "cm": cm,
            "original": text,
        }

    # Pattern: 193 cm
    cm_match = re.match(r"(\d+\.?\d*)\s*cm", text, re.IGNORECASE)
    if cm_match:
        cm = float(cm_match.group(1))
        # Convert to feet and inches
        total_inches = cm / 2.54
        feet = int(total_inches // 12)
        inches = round(total_inches % 12)
        return {
            "value": f"{feet}' {inches}\"",
            "cm": cm,
            "original": text,
        }

    logger.warning(f"Could not parse height: {text}")
    return {"value": text, "cm": None, "original": text}


def parse_sherdog_weight(weight_str: str | None) -> dict[str, Any]:
    """Parse Sherdog weight to normalized format.

    Sherdog formats:
    - "185 lbs" (pounds)
    - "84 kg" (kilograms)

    Args:
        weight_str: Weight string from Sherdog

    Returns:
        Dict with 'value' (normalized to lbs), 'kg', 'original'
    """
    text = clean_text(weight_str)
    if not text:
        return {"value": None, "kg": None, "original": None}

    # Pattern: 185 lbs
    lbs_match = re.match(r"(\d+\.?\d*)\s*lbs?", text, re.IGNORECASE)
    if lbs_match:
        lbs = float(lbs_match.group(1))
        kg = round(lbs * 0.453592, 1)
        return {
            "value": f"{int(lbs)} lbs.",
            "kg": kg,
            "original": text,
        }

    # Pattern: 84 kg
    kg_match = re.match(r"(\d+\.?\d*)\s*kg", text, re.IGNORECASE)
    if kg_match:
        kg = float(kg_match.group(1))
        lbs = round(kg / 0.453592)
        return {
            "value": f"{lbs} lbs.",
            "kg": kg,
            "original": text,
        }

    logger.warning(f"Could not parse weight: {text}")
    return {"value": text, "kg": None, "original": text}


def parse_sherdog_reach(reach_str: str | None) -> dict[str, Any]:
    """Parse Sherdog reach to normalized format.

    Sherdog formats:
    - "84\"" (inches)
    - "213 cm" (centimeters)

    Args:
        reach_str: Reach string from Sherdog

    Returns:
        Dict with 'value' (normalized to inches), 'cm', 'original'
    """
    text = clean_text(reach_str)
    if not text:
        return {"value": None, "cm": None, "original": None}

    # Pattern: 84" or 84.5"
    inches_match = re.match(r"(\d+\.?\d*)\"?", text)
    if inches_match and "cm" not in text.lower():
        inches = float(inches_match.group(1))
        cm = round(inches * 2.54, 1)
        # Format as integer if no decimal part
        if inches == int(inches):
            return {
                "value": f"{int(inches)}\"",
                "cm": cm,
                "original": text,
            }
        return {
            "value": f"{inches}\"",
            "cm": cm,
            "original": text,
        }

    # Pattern: 213 cm
    cm_match = re.match(r"(\d+\.?\d*)\s*cm", text, re.IGNORECASE)
    if cm_match:
        cm = float(cm_match.group(1))
        inches = round(cm / 2.54, 1)
        # Format as integer if no decimal part
        if inches == int(inches):
            return {
                "value": f"{int(inches)}\"",
                "cm": cm,
                "original": text,
            }
        return {
            "value": f"{inches}\"",
            "cm": cm,
            "original": text,
        }

    logger.warning(f"Could not parse reach: {text}")
    return {"value": text, "cm": None, "original": text}


def parse_sherdog_fighter_detail(response: Selector) -> dict[str, Any] | None:
    """Parse Sherdog fighter detail page to extract stats.

    Sherdog fighter pages have stats in a table inside div.bio-holder:
    - AGE / Birthday (DOB) - in span with itemprop="birthDate"
    - HEIGHT - in b with itemprop="height"
    - WEIGHT - in b with itemprop="weight"
    - Nationality - in strong with itemprop="nationality"

    HTML structure:
    <div class="module bio_fighter">
        <div class="bio-holder">
            <table>
                <tr><td>AGE</td><td><b>36</b> / <span itemprop="birthDate">Sep 20, 1989</span></td></tr>
                <tr><td>HEIGHT</td><td><b itemprop="height">6'0"</b> / 182.88 cm</td></tr>
                <tr><td>WEIGHT</td><td><b itemprop="weight">155 lbs</b> / 70.31 kg</td></tr>
            </table>
        </div>
    </div>

    Args:
        response: Scrapy response selector

    Returns:
        Dict with extracted fighter data or None if parsing failed
    """
    try:
        data: dict[str, Any] = {}

        # Extract DOB from birthDate span
        dob_text = clean_text(response.css("span[itemprop='birthDate']::text").get())
        if dob_text:
            data["dob_raw"] = dob_text
            data["dob"] = parse_sherdog_date(dob_text)

        # Extract height from itemprop height
        height_text = clean_text(response.css("b[itemprop='height']::text").get())
        if height_text:
            height_data = parse_sherdog_height(height_text)
            data["height"] = height_data["value"]
            data["height_cm"] = height_data["cm"]

        # Extract weight from itemprop weight
        weight_text = clean_text(response.css("b[itemprop='weight']::text").get())
        if weight_text:
            weight_data = parse_sherdog_weight(weight_text)
            data["weight"] = weight_data["value"]
            data["weight_kg"] = weight_data["kg"]

        # Extract nationality (convert to ISO code)
        nationality_text = clean_text(
            response.css("strong[itemprop='nationality']::text").get()
        )
        if nationality_text:
            nationality = normalize_nationality(nationality_text)
            if nationality:
                data["nationality"] = nationality

        # Try to find reach - look in table rows for "REACH" label
        # Sherdog sometimes has this field, sometimes doesn't
        table_rows = response.css("div.bio-holder table tr")
        for row in table_rows:
            label = clean_text(row.css("td:first-child::text").get())
            if label and "reach" in label.lower():
                reach_text = clean_text(row.css("td:nth-child(2) b::text").get())
                if reach_text:
                    reach_data = parse_sherdog_reach(reach_text)
                    data["reach"] = reach_data["value"]
                    data["reach_cm"] = reach_data["cm"]
                break

        # Try to find stance - also in table rows
        for row in table_rows:
            label = clean_text(row.css("td:first-child::text").get())
            if label and "stance" in label.lower():
                stance_text = clean_text(row.css("td:nth-child(2) b::text").get())
                if stance_text:
                    data["stance"] = stance_text
                break

        # If we got any data, return it
        if data:
            return data

        logger.warning("Could not extract any fighter stats from Sherdog page")
        return None

    except (AttributeError, ValueError, TypeError, KeyError) as e:
        logger.error(f"Error parsing Sherdog fighter detail: {e}")
        return None

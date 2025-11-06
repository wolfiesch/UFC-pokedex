"""Utilities for parsing Sherdog fighter profile pages."""

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

    Sherdog fighter pages typically have a bio module with:
    - Birthday (DOB)
    - Height
    - Weight
    - Reach (listed as "Arm Reach" in some layouts)
    - Stance (Orthodox, Southpaw, etc.)
    - Nationality

    Common HTML patterns:
    - Bio module: div.module.bio_fighter or div.bio
    - Stats in spans with specific classes or in definition list (dt/dd pairs)

    Args:
        response: Scrapy response selector

    Returns:
        Dict with extracted fighter data or None if parsing failed
    """
    try:
        # Find the bio/vitals section
        # Sherdog uses various layouts, so try multiple selectors
        bio_section = (
            response.css("div.module.bio_fighter")
            or response.css("div.bio")
            or response.css("div.content.table")
        )

        if not bio_section:
            logger.warning("Could not find bio section on Sherdog page")
            return None

        data: dict[str, Any] = {}

        # Strategy 1: Look for definition list (dt/dd pairs)
        # Example: <dt>Birthday</dt><dd>1987-07-19</dd>
        bio_items = bio_section.css("div.bio span.item, div.birth_info span.item")

        for item in bio_items:
            # Get label and value
            label = clean_text(item.css("strong::text").get())
            value = clean_text(item.css("::text").getall()[-1] if item.css("::text").getall() else None)

            if not label or not value:
                continue

            label_lower = label.lower().replace(":", "").strip()

            if "birthday" in label_lower or "born" in label_lower:
                data["dob_raw"] = value
                data["dob"] = parse_sherdog_date(value)
            elif "height" in label_lower:
                height_data = parse_sherdog_height(value)
                data["height"] = height_data["value"]
                data["height_cm"] = height_data["cm"]
            elif "weight" in label_lower:
                weight_data = parse_sherdog_weight(value)
                data["weight"] = weight_data["value"]
                data["weight_kg"] = weight_data["kg"]
            elif "reach" in label_lower or "arm reach" in label_lower:
                reach_data = parse_sherdog_reach(value)
                data["reach"] = reach_data["value"]
                data["reach_cm"] = reach_data["cm"]
            elif "stance" in label_lower:
                data["stance"] = value
            elif "nationality" in label_lower:
                data["nationality"] = value

        # Strategy 2: Try alternative selectors if no data found
        if not data:
            # Look for spans with class like "birthdate", "height", etc.
            dob_alt = clean_text(
                bio_section.css("span.birthday::text, span.birthdate::text").get()
            )
            if dob_alt:
                data["dob_raw"] = dob_alt
                data["dob"] = parse_sherdog_date(dob_alt)

            height_alt = clean_text(bio_section.css("span.height::text").get())
            if height_alt:
                height_data = parse_sherdog_height(height_alt)
                data["height"] = height_data["value"]
                data["height_cm"] = height_data["cm"]

            weight_alt = clean_text(bio_section.css("span.weight::text").get())
            if weight_alt:
                weight_data = parse_sherdog_weight(weight_alt)
                data["weight"] = weight_data["value"]
                data["weight_kg"] = weight_data["kg"]

        # If we got any data, return it
        if data:
            return data

        logger.warning("Could not extract any fighter stats from Sherdog page")
        return None

    except Exception as e:
        logger.error(f"Error parsing Sherdog fighter detail: {e}")
        return None

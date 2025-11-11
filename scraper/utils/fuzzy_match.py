"""Fuzzy matching utilities for matching UFC fighters to Sherdog profiles."""

import unicodedata
from typing import Any

from rapidfuzz import fuzz


def normalize_name(name: str) -> str:
    """Normalize fighter name for comparison.

    Strips accents/diacritics and normalizes to ASCII for fuzzy matching.
    Examples:
        - "Jiří Procházka" → "jiri prochazka"
        - "Benoît Saint Denis" → "benoit saint denis"
        - "Jéssica Andrade" → "jessica andrade"
        - "Jan Błachowicz" → "jan blachowicz"

    Args:
        name: Fighter name to normalize

    Returns:
        Normalized name (lowercase, ASCII, stripped, no extra spaces)
    """
    # Manual transliterations for special characters that don't decompose
    # (e.g., Polish Ł, Scandinavian Ø, etc.)
    transliterations = {
        "ł": "l", "Ł": "l",  # Polish L with stroke
        "ø": "o", "Ø": "o",  # Scandinavian O with stroke
        "đ": "d", "Đ": "d",  # Croatian D with stroke
        "þ": "th", "Þ": "th",  # Icelandic thorn
        "ð": "d", "Ð": "d",  # Icelandic eth
        "ß": "ss",  # German sharp S
    }

    # Apply manual transliterations
    for original, replacement in transliterations.items():
        name = name.replace(original, replacement)

    # Decompose Unicode characters (NFD = Canonical Decomposition)
    # e.g., "é" becomes "e" + combining acute accent
    nfd = unicodedata.normalize("NFD", name)

    # Filter out combining characters (diacritics/accents)
    # Keep only base characters
    ascii_name = "".join(
        char for char in nfd
        if unicodedata.category(char) != "Mn"  # Mn = Mark, Nonspacing (diacritics)
    )

    # Lowercase and normalize whitespace
    return " ".join(ascii_name.lower().strip().split())


def normalize_division(division: str | None) -> str:
    """Normalize division name for comparison.

    Args:
        division: Division name (e.g., "Lightweight", "Light Heavyweight")

    Returns:
        Normalized division name
    """
    if not division:
        return ""

    # Normalize common variations
    normalized = division.lower().strip()
    normalized = normalized.replace("weight", "").strip()
    return normalized


def parse_record(record: str | None) -> tuple[int, int, int]:
    """Parse fighter record string into wins, losses, draws.

    Args:
        record: Record string (e.g., "26-1-0", "15-3-0 (1 NC)")

    Returns:
        Tuple of (wins, losses, draws)
    """
    if not record:
        return (0, 0, 0)

    # Handle records with NC (no contest) - strip that part
    if "(" in record:
        record = record.split("(")[0].strip()

    parts = record.split("-")
    if len(parts) >= 3:
        try:
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            pass

    return (0, 0, 0)


def calculate_record_similarity(record1: str | None, record2: str | None) -> float:
    """Calculate similarity between two fight records.

    Args:
        record1: First fighter's record
        record2: Second fighter's record

    Returns:
        Similarity score 0-100 (higher is more similar)
    """
    w1, l1, d1 = parse_record(record1)
    w2, l2, d2 = parse_record(record2)

    # If either record is empty, return low score
    if (w1 == 0 and l1 == 0) or (w2 == 0 and l2 == 0):
        return 0.0

    # Calculate difference in total fights
    total1 = w1 + l1 + d1
    total2 = w2 + l2 + d2

    # Allow some variance in total fights (records may be outdated)
    if total1 == 0 or total2 == 0:
        return 0.0

    fight_diff = abs(total1 - total2)
    max_total = max(total1, total2)

    # If fight totals are very different (>20% difference), low similarity
    if fight_diff / max_total > 0.2:
        return 20.0

    # Calculate similarity based on W-L-D differences
    win_diff = abs(w1 - w2)
    loss_diff = abs(l1 - l2)
    draw_diff = abs(d1 - d2)

    total_diff = win_diff + loss_diff + draw_diff

    # Perfect match = 100, each difference reduces score
    # Allow up to 3 total differences for "good match"
    if total_diff == 0:
        return 100.0
    elif total_diff <= 2:
        return 85.0 - (total_diff * 10)
    elif total_diff <= 5:
        return 65.0 - ((total_diff - 2) * 10)
    else:
        return max(30.0, 60.0 - (total_diff * 5))


def calculate_multi_algorithm_match_score(
    ufcstats_name: str,
    ufc_com_name: str,
) -> dict[str, Any]:
    """Calculate match confidence using multiple fuzzy matching algorithms.

    This is the UFC.com-specific matching function that uses multiple algorithms
    for robust name matching as specified in the design document (lines 502-540).

    Uses weighted scoring:
    - token_sort: 40% (handles word order)
    - token_set: 30% (best for ignoring extra tokens)
    - partial: 20% (handles nicknames, extra words)
    - ratio: 10% (exact character matching)

    Args:
        ufcstats_name: Fighter name from UFCStats database
        ufc_com_name: Fighter name from UFC.com

    Returns:
        Dict with keys:
            - scores: Individual algorithm scores
            - confidence: Final weighted confidence (0-100)
            - normalized_a: Normalized UFCStats name
            - normalized_b: Normalized UFC.com name
    """
    norm_a = normalize_name(ufcstats_name)
    norm_b = normalize_name(ufc_com_name)

    scores = {
        # Token sort: handles word order
        "token_sort": fuzz.token_sort_ratio(norm_a, norm_b),
        # Partial: handles nicknames, extra words
        "partial": fuzz.partial_ratio(norm_a, norm_b),
        # Simple ratio: exact character matching
        "ratio": fuzz.ratio(norm_a, norm_b),
        # Token set: best for ignoring extra tokens
        "token_set": fuzz.token_set_ratio(norm_a, norm_b),
    }

    # Weighted average (token_sort and token_set most reliable)
    final_score = (
        scores["token_sort"] * 0.4
        + scores["token_set"] * 0.3
        + scores["partial"] * 0.2
        + scores["ratio"] * 0.1
    )

    return {
        "scores": scores,
        "confidence": round(final_score, 2),
        "normalized_a": norm_a,
        "normalized_b": norm_b,
    }


def calculate_match_confidence(
    ufc_fighter: dict[str, Any],
    sherdog_result: dict[str, Any],
) -> float:
    """Calculate confidence score for a UFC-Sherdog fighter match.

    Uses weighted scoring:
    - Name similarity: 60% weight
    - Division match: 20% weight
    - Record similarity: 20% weight

    Args:
        ufc_fighter: UFC fighter data (name, division, record)
        sherdog_result: Sherdog search result (name, division, record)

    Returns:
        Confidence score 0-100 (higher = more confident match)
    """
    # Name matching (60% weight)
    ufc_name = normalize_name(ufc_fighter.get("name", ""))
    sherdog_name = normalize_name(sherdog_result.get("name", ""))

    # Use token set ratio for better handling of name variations
    name_score = fuzz.token_set_ratio(ufc_name, sherdog_name)

    # Division matching (20% weight)
    ufc_division = normalize_division(ufc_fighter.get("division"))
    sherdog_division = normalize_division(sherdog_result.get("division"))

    if ufc_division and sherdog_division:
        division_score = fuzz.ratio(ufc_division, sherdog_division)
    else:
        # If one or both divisions are missing, neutral score
        division_score = 50.0

    # Record matching (20% weight)
    ufc_record = ufc_fighter.get("record")
    sherdog_record = sherdog_result.get("record")
    record_score = calculate_record_similarity(ufc_record, sherdog_record)

    # Weighted average
    confidence = (
        name_score * 0.6 +
        division_score * 0.2 +
        record_score * 0.2
    )

    return round(confidence, 2)


def is_high_confidence_match(confidence: float) -> bool:
    """Check if a match confidence is high enough for auto-approval.

    Args:
        confidence: Confidence score 0-100

    Returns:
        True if confidence >= 90% (high confidence)
    """
    return confidence >= 90.0


def is_ambiguous_match(confidence: float) -> bool:
    """Check if a match is ambiguous and needs manual verification.

    Args:
        confidence: Confidence score 0-100

    Returns:
        True if confidence is between 60-90% (needs review)
    """
    return 60.0 <= confidence < 90.0


def is_low_confidence_match(confidence: float) -> bool:
    """Check if a match confidence is too low to be useful.

    Args:
        confidence: Confidence score 0-100

    Returns:
        True if confidence < 60% (reject match)
    """
    return confidence < 60.0


def calculate_disambiguation_score(
    ufc_com_fighter: dict[str, Any],
    ufcstats_fighter: dict[str, Any],
    name_confidence: float,
) -> dict[str, Any]:
    """Use additional signals beyond name matching for disambiguation.

    This function implements the disambiguation logic specified in the design
    document (lines 548-611) to resolve duplicate fighter names.

    Signal weights:
    - Division match: +15 points (STRONGEST)
    - Record similarity: +10 or -20 points (MEDIUM)
    - Age/DOB proximity: +5 or -15 points (MEDIUM)
    - Weight class plausibility: +3 or -10 points (WEAK)

    Args:
        ufc_com_fighter: UFC.com fighter data (division, record, age, weight)
        ufcstats_fighter: UFCStats fighter data (division, record, dob, weight)
        name_confidence: Base name matching confidence (0-100)

    Returns:
        Dict with keys:
            - base_confidence: Original name confidence
            - bonus_points: Total bonus/penalty points applied
            - final_confidence: Adjusted confidence (0-100)
            - signals: Dict of individual signal results
    """
    bonus_points = 0
    signals = {}

    # Signal 1: Division match (STRONGEST - +15 points)
    ufc_com_division = ufc_com_fighter.get("division")
    ufcstats_division = ufcstats_fighter.get("division")

    if ufc_com_division and ufcstats_division:
        division_match = normalize_division(ufc_com_division) == normalize_division(
            ufcstats_division
        )
        signals["division_match"] = division_match
        if division_match:
            bonus_points += 15

    # Signal 2: Record similarity (MEDIUM - +10 or -20 points)
    ufc_com_record = ufc_com_fighter.get("record")
    ufcstats_record = ufcstats_fighter.get("record")

    if ufc_com_record and ufcstats_record:
        record_similarity = calculate_record_similarity(ufc_com_record, ufcstats_record)
        signals["record_similarity"] = record_similarity / 100.0  # Normalize to 0-1
        if record_similarity >= 80.0:
            bonus_points += 10
        elif record_similarity <= 30.0:
            bonus_points -= 20  # Penalty - likely different fighters

    # Signal 3: Age/DOB proximity (MEDIUM - +5 or -15 points)
    ufc_com_age = ufc_com_fighter.get("age")
    ufcstats_dob = ufcstats_fighter.get("dob")

    if ufc_com_age and ufcstats_dob:
        ufcstats_age = calculate_age(ufcstats_dob)
        if ufcstats_age:
            age_diff = abs(ufc_com_age - ufcstats_age)
            signals["age_diff"] = age_diff
            if age_diff <= 1:
                bonus_points += 5
            elif age_diff >= 5:
                bonus_points -= 15

    # Signal 4: Weight class plausibility (WEAK - +3 or -10 points)
    ufc_com_weight = ufc_com_fighter.get("weight")
    ufcstats_weight = ufcstats_fighter.get("weight")

    if ufc_com_weight and ufcstats_weight:
        weight_diff = calculate_weight_difference(
            str(ufc_com_weight), str(ufcstats_weight)
        )
        signals["weight_diff_lbs"] = weight_diff
        if weight_diff <= 10:
            bonus_points += 3
        elif weight_diff >= 40:
            bonus_points -= 10

    final_confidence = name_confidence + bonus_points

    return {
        "base_confidence": name_confidence,
        "bonus_points": bonus_points,
        "final_confidence": min(100, max(0, final_confidence)),
        "signals": signals,
    }


def calculate_age(dob: str | None) -> int | None:
    """Calculate age from date of birth string.

    Args:
        dob: Date of birth string (YYYY-MM-DD format)

    Returns:
        Age in years, or None if DOB is invalid
    """
    if not dob:
        return None

    from datetime import datetime

    try:
        dob_date = datetime.strptime(dob.split("T")[0], "%Y-%m-%d")
        today = datetime.now()
        age = today.year - dob_date.year
        # Adjust if birthday hasn't occurred yet this year
        if (today.month, today.day) < (dob_date.month, dob_date.day):
            age -= 1
        return age
    except (ValueError, AttributeError):
        return None


def calculate_weight_difference(weight1: str | None, weight2: str | None) -> float:
    """Calculate absolute difference between two weight values in pounds.

    Args:
        weight1: First weight (e.g., "155.00", "155 lbs", "70 kg")
        weight2: Second weight in same or different units

    Returns:
        Absolute weight difference in pounds
    """
    if not weight1 or not weight2:
        return 999.0  # Large value indicates no comparison possible

    def parse_weight(weight: str) -> float | None:
        """Parse weight string to pounds."""
        try:
            # Remove whitespace
            weight = weight.strip()

            # Extract numeric value
            import re
            match = re.search(r"(\d+\.?\d*)", weight)
            if not match:
                return None

            value = float(match.group(1))

            # Convert kg to lbs if needed
            if "kg" in weight.lower():
                value *= 2.20462

            return value
        except (ValueError, AttributeError):
            return None

    w1 = parse_weight(str(weight1))
    w2 = parse_weight(str(weight2))

    if w1 is None or w2 is None:
        return 999.0

    return abs(w1 - w2)

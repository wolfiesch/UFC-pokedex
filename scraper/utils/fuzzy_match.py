"""Fuzzy matching utilities for matching UFC fighters to Sherdog profiles."""

from rapidfuzz import fuzz
from typing import Any


def normalize_name(name: str) -> str:
    """Normalize fighter name for comparison.

    Args:
        name: Fighter name to normalize

    Returns:
        Normalized name (lowercase, stripped, no extra spaces)
    """
    return " ".join(name.lower().strip().split())


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

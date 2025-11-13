"""
Bookmaker ID mapping for BestFightOdds.com

Based on the website header row, these are the active major bookmakers.
Use this to filter out deprecated/suspicious bookmakers.
"""

MAJOR_BOOKMAKERS = {
    19: "Bet365",
    20: "BetWay",
    21: "FanDuel",
    22: "DraftKings",
    23: "BetMGM",
    24: "Caesars",
    25: "BetRivers",
    26: "Unibet",
    27: "PointsBet",
}

# Recommended filter for most reliable odds
TIER_1_BOOKMAKERS = {
    21: "FanDuel",
    22: "DraftKings",
    23: "BetMGM",
    24: "Caesars",
}

# Old/deprecated bookmakers (may have suspicious odds)
DEPRECATED_BOOKMAKERS = {
    1: "Unknown/Deprecated 1",
    2: "Unknown/Deprecated 2",
}


def is_major_bookmaker(bookmaker_id: int) -> bool:
    """Check if bookmaker ID is a major active bookmaker."""
    return bookmaker_id in MAJOR_BOOKMAKERS


def is_tier1_bookmaker(bookmaker_id: int) -> bool:
    """Check if bookmaker ID is tier 1 (FanDuel, DraftKings, BetMGM, Caesars)."""
    return bookmaker_id in TIER_1_BOOKMAKERS


def get_bookmaker_name(bookmaker_id: int) -> str:
    """Get bookmaker name from ID."""
    if bookmaker_id in MAJOR_BOOKMAKERS:
        return MAJOR_BOOKMAKERS[bookmaker_id]
    if bookmaker_id in DEPRECATED_BOOKMAKERS:
        return DEPRECATED_BOOKMAKERS[bookmaker_id]
    return f"Unknown ({bookmaker_id})"


def filter_major_bookmakers(odds_data: dict) -> dict:
    """
    Filter odds data to only include major bookmakers.

    Args:
        odds_data: Odds dict with 'bookmakers' list

    Returns:
        Filtered odds dict with only major bookmakers
    """
    if not odds_data or not odds_data.get("bookmakers"):
        return odds_data

    filtered_bookmakers = [
        bm for bm in odds_data["bookmakers"] if is_major_bookmaker(bm.get("bookmaker_id"))
    ]

    return {"bookmakers": filtered_bookmakers, "count": len(filtered_bookmakers)}


def filter_tier1_bookmakers(odds_data: dict) -> dict:
    """
    Filter odds data to only include tier 1 bookmakers.

    Args:
        odds_data: Odds dict with 'bookmakers' list

    Returns:
        Filtered odds dict with only tier 1 bookmakers
    """
    if not odds_data or not odds_data.get("bookmakers"):
        return odds_data

    filtered_bookmakers = [
        bm for bm in odds_data["bookmakers"] if is_tier1_bookmaker(bm.get("bookmaker_id"))
    ]

    return {"bookmakers": filtered_bookmakers, "count": len(filtered_bookmakers)}

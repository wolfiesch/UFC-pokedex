"""Name matching utility for UFC rankings to fighter database matching.

This module provides functionality to match fighter names from UFC rankings
(which may use different naming conventions) to fighter IDs in the database.
Uses fuzzy string matching with record-based tiebreaking for high accuracy.
"""

from typing import Any

from rapidfuzz import fuzz, process

from scraper.utils.fuzzy_match import (
    calculate_record_similarity,
    normalize_name,
)


class FighterNameMatcher:
    """Matches fighter names from rankings to database fighter IDs."""

    def __init__(self, fighters_db: list[dict[str, Any]]):
        """Initialize the name matcher with a fighter database.

        Args:
            fighters_db: List of fighter dicts with keys: id, name, record, division
        """
        self.fighters_db = fighters_db
        # Build normalized name lookup for faster matching
        self.name_lookup = {
            normalize_name(f["name"]): f for f in fighters_db
        }

    def match_fighter(
        self,
        ranking_name: str,
        division: str | None = None,
        min_confidence: float = 80.0,
    ) -> tuple[str | None, float, str]:
        """Match a fighter name from rankings to a database fighter ID.

        Uses fuzzy string matching with optional record-based tiebreaking.
        Confidence threshold is 80% by default (as specified in plan).

        Args:
            ranking_name: Fighter name from rankings source
            division: Optional division for additional validation
            min_confidence: Minimum confidence threshold (0-100)

        Returns:
            Tuple of (fighter_id, confidence_score, match_reason)
            Returns (None, 0.0, reason) if no match found
        """
        normalized_input = normalize_name(ranking_name)

        # Try exact match first (fastest path)
        if normalized_input in self.name_lookup:
            fighter = self.name_lookup[normalized_input]
            return (fighter["id"], 100.0, "exact_name_match")

        # Fuzzy match against all fighter names
        # Use list of (choice, context) tuples to preserve all candidates with duplicate names
        name_choices = [
            (normalize_name(f["name"]), f) for f in self.fighters_db
        ]

        # Use rapidfuzz's process.extractOne with processor to handle tuples
        match_result = process.extractOne(
            normalized_input,
            name_choices,
            scorer=fuzz.token_set_ratio,
            processor=lambda x: x[0],  # Extract normalized name from tuple
        )

        if not match_result:
            return (None, 0.0, "no_fuzzy_match_found")

        (matched_name, matched_fighter), name_confidence, _ = match_result

        # Check if name confidence alone is sufficient
        if name_confidence >= min_confidence:
            # Optional: Verify division matches if provided
            if division:
                fighter_division = matched_fighter.get("division")
                if fighter_division and fighter_division.lower() != division.lower():
                    # Penalize division mismatch and re-check threshold
                    adjusted_confidence = name_confidence * 0.9
                    if adjusted_confidence < min_confidence:
                        # Division mismatch drops confidence below threshold - reject
                        return (
                            None,
                            adjusted_confidence,
                            f"rejected_division_mismatch (expected: {division}, got: {fighter_division})",
                        )
                    return (
                        matched_fighter["id"],
                        adjusted_confidence,
                        f"name_match_division_mismatch (expected: {division}, got: {fighter_division})",
                    )

            return (
                matched_fighter["id"],
                name_confidence,
                "high_confidence_name_match",
            )

        # Below threshold - no record tiebreaker available (rankings don't include records)
        # Operator should manually review matches in 70-79% range
        return (
            None,
            round(name_confidence, 2),
            f"below_confidence_threshold (threshold={min_confidence}, score={name_confidence:.2f})",
        )

    # NOTE: _boost_confidence_with_record method removed
    # Rankings sources (UFC.com, Fight Matrix) don't include fighter records,
    # so record-based tiebreaking is not possible. Matches below 80% confidence
    # are rejected and require manual review.

    def match_multiple(
        self,
        ranking_names: list[str],
        division: str | None = None,
        min_confidence: float = 80.0,
    ) -> list[dict[str, Any]]:
        """Match multiple fighter names at once.

        Args:
            ranking_names: List of fighter names from rankings
            division: Optional division for validation
            min_confidence: Minimum confidence threshold

        Returns:
            List of dicts with keys:
                - ranking_name: Original name
                - fighter_id: Matched ID (or None)
                - confidence: Match confidence
                - match_reason: Why this match was made/rejected
        """
        results = []
        for name in ranking_names:
            fighter_id, confidence, reason = self.match_fighter(
                name, division, min_confidence
            )
            results.append({
                "ranking_name": name,
                "fighter_id": fighter_id,
                "confidence": confidence,
                "match_reason": reason,
            })
        return results

    def get_match_statistics(self, match_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate statistics for a batch of match results.

        Args:
            match_results: Output from match_multiple()

        Returns:
            Dict with statistics:
                - total: Total names processed
                - matched: Number of successful matches
                - unmatched: Number of failed matches
                - match_rate: Percentage matched
                - avg_confidence: Average confidence of matches
        """
        total = len(match_results)
        matched = sum(1 for r in match_results if r["fighter_id"] is not None)
        unmatched = total - matched

        matched_confidences = [
            r["confidence"] for r in match_results if r["fighter_id"] is not None
        ]
        avg_confidence = (
            sum(matched_confidences) / len(matched_confidences)
            if matched_confidences else 0.0
        )

        return {
            "total": total,
            "matched": matched,
            "unmatched": unmatched,
            "match_rate": round((matched / total * 100) if total > 0 else 0.0, 2),
            "avg_confidence": round(avg_confidence, 2),
        }

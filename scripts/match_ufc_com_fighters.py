#!/usr/bin/env python3
"""Match UFC.com fighters to UFCStats database using fuzzy matching.

This script implements Phase 3 of the Fighter Geographical Data plan.
It uses multi-algorithm fuzzy matching with disambiguation signals to
link UFC.com fighter profiles to UFCStats database IDs.

Usage:
    python scripts/match_ufc_com_fighters.py
    python scripts/match_ufc_com_fighters.py --min-confidence 85
    python scripts/match_ufc_com_fighters.py --dry-run

Output:
    - data/processed/ufc_com_matches.jsonl - All matches with confidence scores
    - data/processed/ufc_com_matches_manual_review.jsonl - Low-confidence matches
"""

import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

import click
import psycopg


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scraper.utils.fuzzy_match import (
    calculate_disambiguation_score,
    calculate_multi_algorithm_match_score,
    normalize_name,
)


def load_ufcstats_fighters(db_url: str | None = None) -> list[dict[str, Any]]:
    """Load all fighters from UFCStats database.

    Args:
        db_url: PostgreSQL database URL (defaults to DATABASE_URL env var)

    Returns:
        List of fighter dicts with id, name, division, record, dob, weight
    """
    if db_url is None:
        db_url = os.getenv("DATABASE_URL", "postgresql://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex")

    conn = psycopg.connect(db_url)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name, division, record, dob, weight
        FROM fighters
        ORDER BY name
        """
    )

    fighters = [
        {
            "id": row[0],
            "name": row[1],
            "division": row[2],
            "record": row[3],
            "dob": row[4],
            "weight": row[5],
        }
        for row in cursor.fetchall()
    ]
    conn.close()

    click.echo(f"Loaded {len(fighters)} fighters from UFCStats database")
    return fighters


def load_ufc_com_fighters(ufc_com_dir: Path) -> list[dict[str, Any]]:
    """Load all UFC.com fighter profiles from JSON files.

    Args:
        ufc_com_dir: Directory containing UFC.com fighter JSON files

    Returns:
        List of fighter dicts from UFC.com
    """
    fighters = []

    for json_file in ufc_com_dir.glob("*.json"):
        with open(json_file) as f:
            fighter = json.load(f)
            fighters.append(fighter)

    click.echo(f"Loaded {len(fighters)} fighters from UFC.com data")
    return fighters


def find_candidate_matches(
    ufc_com_fighter: dict[str, Any],
    ufcstats_fighters: list[dict[str, Any]],
    min_name_confidence: float = 50.0,
) -> list[dict[str, Any]]:
    """Find all candidate matches for a UFC.com fighter.

    Args:
        ufc_com_fighter: UFC.com fighter data
        ufcstats_fighters: List of all UFCStats fighters
        min_name_confidence: Minimum name confidence to consider

    Returns:
        List of candidate matches with confidence scores
    """
    ufc_com_name = ufc_com_fighter.get("name", "")
    candidates = []

    for ufcstats_fighter in ufcstats_fighters:
        ufcstats_name = ufcstats_fighter.get("name", "")

        # Calculate name match score
        match_result = calculate_multi_algorithm_match_score(
            ufcstats_name, ufc_com_name
        )
        name_confidence = match_result["confidence"]

        # Skip low-confidence name matches
        if name_confidence < min_name_confidence:
            continue

        # Calculate disambiguation score with additional signals
        disambiguation = calculate_disambiguation_score(
            ufc_com_fighter, ufcstats_fighter, name_confidence
        )

        candidate = {
            "ufcstats_id": ufcstats_fighter["id"],
            "ufcstats_name": ufcstats_name,
            "ufcstats_division": ufcstats_fighter.get("division"),
            "ufcstats_record": ufcstats_fighter.get("record"),
            "ufcstats_dob": ufcstats_fighter.get("dob"),
            "ufcstats_weight": ufcstats_fighter.get("weight"),
            "name_confidence": name_confidence,
            "base_confidence": disambiguation["base_confidence"],
            "bonus_points": disambiguation["bonus_points"],
            "final_confidence": disambiguation["final_confidence"],
            "signals": disambiguation["signals"],
            "match_scores": match_result["scores"],
        }

        candidates.append(candidate)

    # Sort by final confidence (highest first)
    candidates.sort(key=lambda x: x["final_confidence"], reverse=True)

    return candidates


def classify_match(
    final_confidence: float, confidence_gap: float
) -> tuple[str, bool]:
    """Classify match quality and determine if manual review is needed.

    Thresholds from design document (lines 616-634):
    - auto_high: >=95 confidence AND >=15 point gap
    - auto_medium: >=85 confidence
    - manual_review: 70-84 confidence
    - no_match: <70 confidence

    Args:
        final_confidence: Final confidence score (0-100)
        confidence_gap: Difference between top and second match

    Returns:
        Tuple of (classification, needs_manual_review)
    """
    if final_confidence >= 95 and confidence_gap >= 15:
        return ("auto_high", False)
    elif final_confidence >= 85:
        return ("auto_medium", False)
    elif final_confidence >= 70:
        return ("manual_review", True)
    else:
        return ("no_match", False)


def match_fighters(
    ufc_com_fighters: list[dict[str, Any]],
    ufcstats_fighters: list[dict[str, Any]],
    min_name_confidence: float = 50.0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Match all UFC.com fighters to UFCStats database.

    Args:
        ufc_com_fighters: List of UFC.com fighter data
        ufcstats_fighters: List of UFCStats fighter data
        min_name_confidence: Minimum name confidence for candidates

    Returns:
        Tuple of (all_matches, manual_review_matches)
    """
    all_matches = []
    manual_review_matches = []
    matched_fighters: dict[str, str] = {}

    stats = {
        "total": len(ufc_com_fighters),
        "auto_high": 0,
        "auto_medium": 0,
        "manual_review": 0,
        "no_match": 0,
        "duplicates_detected": 0,
        "duplicate_conflicts": 0,
    }

    click.echo("\nMatching UFC.com fighters to UFCStats database...\n")

    for ufc_com_fighter in ufc_com_fighters:
        ufc_com_name = ufc_com_fighter.get("name", "")
        ufc_com_slug = ufc_com_fighter.get("slug", "")

        click.echo(f"Matching: {ufc_com_name} ({ufc_com_slug})")

        # Find all candidate matches
        candidates = find_candidate_matches(
            ufc_com_fighter, ufcstats_fighters, min_name_confidence
        )

        if not candidates:
            click.echo("  No match found\n")
            stats["no_match"] += 1
            continue

        # Get top match and confidence gap
        top_match = candidates[0]
        confidence_gap = (
            top_match["final_confidence"] - candidates[1]["final_confidence"]
            if len(candidates) > 1
            else 100.0
        )

        # Classify match quality
        classification, needs_review = classify_match(
            top_match["final_confidence"], confidence_gap
        )

        match_record = {
            "ufc_com_slug": ufc_com_slug,
            "ufc_com_name": ufc_com_name,
            "ufc_com_division": ufc_com_fighter.get("division"),
            "ufc_com_record": ufc_com_fighter.get("record"),
            "ufc_com_age": ufc_com_fighter.get("age"),
            "ufc_com_weight": ufc_com_fighter.get("weight"),
            "ufcstats_id": top_match["ufcstats_id"],
            "ufcstats_name": top_match["ufcstats_name"],
            "confidence": top_match["final_confidence"],
            "classification": classification,
            "confidence_gap": confidence_gap,
            "needs_manual_review": needs_review,
            "signals": top_match["signals"],
            "match_scores": top_match["match_scores"],
        }

        existing_slug = matched_fighters.get(top_match["ufcstats_id"])
        if existing_slug:
            click.echo(
                f"  ⚠️ Duplicate detected: {top_match['ufcstats_id']} is already matched to {existing_slug}. "
                "Routing to manual review."
            )
            stats["duplicate_conflicts"] += 1

            manual_review_matches.append(
                {
                    "reason": "duplicate_conflict",
                    "conflicting_slug": existing_slug,
                    "candidate_slug": ufc_com_slug,
                    "recommended_match": top_match["ufcstats_id"],
                    "classification": classification,
                    "confidence": top_match["final_confidence"],
                    "ufc_com_fighter": {
                        "name": ufc_com_name,
                        "slug": ufc_com_slug,
                        "division": ufc_com_fighter.get("division"),
                        "record": ufc_com_fighter.get("record"),
                    },
                }
            )
            stats["manual_review"] += 1
            click.echo()
            continue

        all_matches.append(match_record)
        matched_fighters[top_match["ufcstats_id"]] = ufc_com_slug

        # Log result
        click.echo(
            f"  Matched to: {top_match['ufcstats_name']} "
            f"(confidence: {top_match['final_confidence']:.1f}, "
            f"classification: {classification})"
        )

        if len(candidates) > 1:
            click.echo(f"  Confidence gap: {confidence_gap:.1f} points")
            stats["duplicates_detected"] += 1

        # Add to manual review if needed
        if needs_review:
            manual_review_record = {
                "ufc_com_fighter": {
                    "name": ufc_com_name,
                    "slug": ufc_com_slug,
                    "division": ufc_com_fighter.get("division"),
                    "record": ufc_com_fighter.get("record"),
                    "age": ufc_com_fighter.get("age"),
                    "weight": ufc_com_fighter.get("weight"),
                },
                "candidates": [
                    {
                        "id": c["ufcstats_id"],
                        "name": c["ufcstats_name"],
                        "division": c["ufcstats_division"],
                        "record": c["ufcstats_record"],
                        "dob": c["ufcstats_dob"],
                        "final_confidence": c["final_confidence"],
                        "signals": c["signals"],
                    }
                    for c in candidates[:3]  # Top 3 candidates
                ],
                "recommended_match": top_match["ufcstats_id"],
                "confidence_gap": confidence_gap,
                "status": (
                    "resolved_duplicate"
                    if len(candidates) > 1
                    else "borderline_confidence"
                ),
            }
            manual_review_matches.append(manual_review_record)

        stats[classification] += 1
        click.echo()

    # Print summary
    click.echo("=" * 60)
    click.echo("MATCHING SUMMARY")
    click.echo("=" * 60)
    click.echo(f"Total UFC.com fighters: {stats['total']}")
    click.echo(f"Auto-high confidence: {stats['auto_high']}")
    click.echo(f"Auto-medium confidence: {stats['auto_medium']}")
    click.echo(f"Manual review needed: {stats['manual_review']}")
    click.echo(f"No match found: {stats['no_match']}")
    click.echo(f"Duplicates detected: {stats['duplicates_detected']}")
    if stats["duplicate_conflicts"]:
        click.echo(f"Slug conflicts routed to manual review: {stats['duplicate_conflicts']}")
    click.echo()
    click.echo(
        f"Match rate: {(stats['auto_high'] + stats['auto_medium'] + stats['manual_review']) / stats['total'] * 100:.1f}%"
    )
    click.echo()

    return all_matches, manual_review_matches


@click.command()
@click.option(
    "--db-url",
    default=None,
    help="PostgreSQL database URL (defaults to DATABASE_URL env var)",
    type=str,
)
@click.option(
    "--ufc-com-dir",
    default="data/processed/ufc_com_fighters",
    help="Directory with UFC.com fighter JSON files",
    type=click.Path(exists=True),
)
@click.option(
    "--output",
    default="data/processed/ufc_com_matches.jsonl",
    help="Output path for all matches",
    type=click.Path(),
)
@click.option(
    "--manual-review-output",
    default="data/processed/ufc_com_matches_manual_review.jsonl",
    help="Output path for manual review matches",
    type=click.Path(),
)
@click.option(
    "--min-confidence",
    default=50.0,
    help="Minimum name confidence for candidate matches",
    type=float,
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview matches without writing output files",
)
def main(
    db_url: str | None,
    ufc_com_dir: str,
    output: str,
    manual_review_output: str,
    min_confidence: float,
    dry_run: bool,
):
    """Match UFC.com fighters to UFCStats database using fuzzy matching."""
    click.echo("=" * 60)
    click.echo("UFC.com Fighter Matching Script")
    click.echo("=" * 60)
    click.echo()

    # Load data
    ufcstats_fighters = load_ufcstats_fighters(db_url)
    ufc_com_fighters = load_ufc_com_fighters(Path(ufc_com_dir))

    if not ufc_com_fighters:
        click.echo("Error: No UFC.com fighter data found!", err=True)
        return

    # Match fighters
    all_matches, manual_review_matches = match_fighters(
        ufc_com_fighters, ufcstats_fighters, min_confidence
    )

    # Write output files
    if not dry_run:
        # Write all matches
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            for match in all_matches:
                f.write(json.dumps(match, default=json_serial) + "\n")

        click.echo(f"Wrote {len(all_matches)} matches to {output_path}")

        # Write manual review matches
        if manual_review_matches:
            manual_review_path = Path(manual_review_output)
            with open(manual_review_path, "w") as f:
                for match in manual_review_matches:
                    f.write(json.dumps(match, default=json_serial) + "\n")

            click.echo(
                f"Wrote {len(manual_review_matches)} manual review cases to {manual_review_path}"
            )
    else:
        click.echo("\nDRY RUN - No files written")


if __name__ == "__main__":
    main()

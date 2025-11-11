#!/usr/bin/env python3
"""Interactive CLI tool to review UFC.com to UFCStats fighter matches.

This tool allows manual review and verification of low-confidence matches
identified by the match_ufc_com_fighters.py script.

Usage:
    python scripts/review_matches.py
    python scripts/review_matches.py --input data/processed/ufc_com_matches_manual_review.jsonl
"""

import json
import sys
from pathlib import Path
from typing import Any

import click

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def display_fighter_comparison(review_case: dict[str, Any]) -> None:
    """Display a fighter and their candidate matches for review.

    Args:
        review_case: Manual review case from matches_manual_review.jsonl
    """
    ufc_com = review_case["ufc_com_fighter"]
    candidates = review_case["candidates"]
    recommended = review_case["recommended_match"]
    confidence_gap = review_case["confidence_gap"]
    status = review_case["status"]

    click.echo("\n" + "=" * 70)
    click.echo("FIGHTER MATCH REVIEW")
    click.echo("=" * 70)
    click.echo()

    # Display UFC.com fighter
    click.echo(click.style("UFC.com Fighter:", fg="cyan", bold=True))
    click.echo(f"  Name: {ufc_com['name']}")
    click.echo(f"  Slug: {ufc_com['slug']}")
    if ufc_com.get("division"):
        click.echo(f"  Division: {ufc_com['division']}")
    if ufc_com.get("record"):
        click.echo(f"  Record: {ufc_com['record']}")
    if ufc_com.get("age"):
        click.echo(f"  Age: {ufc_com['age']}")
    if ufc_com.get("weight"):
        click.echo(f"  Weight: {ufc_com['weight']}")
    click.echo()

    # Display match status
    click.echo(click.style(f"Status: {status}", fg="yellow", bold=True))
    click.echo(f"Confidence gap: {confidence_gap:.1f} points")
    click.echo()

    # Display candidates
    click.echo(click.style("Candidate Matches:", fg="cyan", bold=True))
    for i, candidate in enumerate(candidates, 1):
        is_recommended = candidate["id"] == recommended
        color = "green" if is_recommended else "white"
        prefix = "✓ RECOMMENDED" if is_recommended else f"  Candidate #{i}"

        click.echo()
        click.echo(click.style(f"{prefix}", fg=color, bold=is_recommended))
        click.echo(f"  ID: {candidate['id']}")
        click.echo(f"  Name: {candidate['name']}")
        click.echo(
            f"  Confidence: {candidate['final_confidence']:.1f} "
            f"({click.style('HIGH', fg='green') if candidate['final_confidence'] >= 85 else click.style('MEDIUM', fg='yellow')})"
        )

        if candidate.get("division"):
            click.echo(f"  Division: {candidate['division']}")
        if candidate.get("record"):
            click.echo(f"  Record: {candidate['record']}")
        if candidate.get("dob"):
            click.echo(f"  DOB: {candidate['dob']}")

        # Display signals
        signals = candidate.get("signals", {})
        if signals:
            click.echo("  Signals:")
            if "division_match" in signals:
                match_str = (
                    click.style("✓ Match", fg="green")
                    if signals["division_match"]
                    else click.style("✗ Mismatch", fg="red")
                )
                click.echo(f"    - Division: {match_str}")
            if "record_similarity" in signals:
                sim = signals["record_similarity"]
                click.echo(f"    - Record similarity: {sim:.2f}")
            if "age_diff" in signals:
                click.echo(f"    - Age difference: {signals['age_diff']} years")
            if "weight_diff_lbs" in signals:
                click.echo(f"    - Weight difference: {signals['weight_diff_lbs']:.1f} lbs")

    click.echo()


def prompt_for_decision(candidates: list[dict[str, Any]]) -> tuple[str, str | None]:
    """Prompt user for match decision.

    Args:
        candidates: List of candidate matches

    Returns:
        Tuple of (action, fighter_id)
        action: "accept", "select", "skip"
        fighter_id: Selected fighter ID (or None for skip)
    """
    click.echo("=" * 70)
    click.echo("What would you like to do?")
    click.echo()
    click.echo("  [A] Accept recommended match")
    click.echo("  [1-9] Select candidate by number")
    click.echo("  [S] Skip this fighter")
    click.echo("  [Q] Quit review session")
    click.echo()

    while True:
        choice = click.prompt("Your choice", type=str).strip().upper()

        if choice == "A":
            return ("accept", None)
        elif choice == "S":
            return ("skip", None)
        elif choice == "Q":
            return ("quit", None)
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(candidates):
                return ("select", candidates[idx]["id"])
            else:
                click.echo(
                    f"Invalid choice. Please enter 1-{len(candidates)}", err=True
                )
        else:
            click.echo("Invalid choice. Please try again.", err=True)


@click.command()
@click.option(
    "--input",
    "input_file",
    default="data/processed/ufc_com_matches_manual_review.jsonl",
    help="Path to manual review JSONL file",
    type=click.Path(exists=True),
)
@click.option(
    "--output",
    "output_file",
    default="data/processed/ufc_com_matches_verified.jsonl",
    help="Path to output verified matches",
    type=click.Path(),
)
def main(input_file: str, output_file: str):
    """Interactive CLI tool to review fighter matches."""
    click.echo("=" * 70)
    click.echo("UFC.com Fighter Match Review Tool")
    click.echo("=" * 70)
    click.echo()

    # Load manual review cases
    review_cases = []
    with open(input_file) as f:
        for line in f:
            review_cases.append(json.loads(line))

    if not review_cases:
        click.echo("No manual review cases found. All matches are high confidence!")
        return

    click.echo(f"Loaded {len(review_cases)} cases for manual review")
    click.echo()

    # Process each case
    verified_matches = []
    stats = {
        "total": len(review_cases),
        "accepted": 0,
        "selected_different": 0,
        "skipped": 0,
    }

    for i, case in enumerate(review_cases, 1):
        click.echo(f"\nReviewing case {i}/{len(review_cases)}")

        # Display the case
        display_fighter_comparison(case)

        # Get user decision
        action, fighter_id = prompt_for_decision(case["candidates"])

        if action == "quit":
            click.echo("\nQuitting review session...")
            break
        elif action == "skip":
            click.echo(click.style("Skipped", fg="yellow"))
            stats["skipped"] += 1
        elif action == "accept":
            verified_match = {
                "ufc_com_slug": case["ufc_com_fighter"]["slug"],
                "ufc_com_name": case["ufc_com_fighter"]["name"],
                "ufcstats_id": case["recommended_match"],
                "confidence": case["candidates"][0]["final_confidence"],
                "classification": "manual_verified",
                "verification_action": "accepted_recommended",
            }
            verified_matches.append(verified_match)
            click.echo(click.style("✓ Accepted recommended match", fg="green"))
            stats["accepted"] += 1
        elif action == "select":
            # Find the selected candidate
            selected_candidate = next(
                c for c in case["candidates"] if c["id"] == fighter_id
            )
            verified_match = {
                "ufc_com_slug": case["ufc_com_fighter"]["slug"],
                "ufc_com_name": case["ufc_com_fighter"]["name"],
                "ufcstats_id": fighter_id,
                "confidence": selected_candidate["final_confidence"],
                "classification": "manual_verified",
                "verification_action": "selected_alternative",
            }
            verified_matches.append(verified_match)
            click.echo(
                click.style(
                    f"✓ Selected alternative match: {selected_candidate['name']}",
                    fg="green",
                )
            )
            stats["selected_different"] += 1

    # Save verified matches
    if verified_matches:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            for match in verified_matches:
                f.write(json.dumps(match) + "\n")

        click.echo()
        click.echo("=" * 70)
        click.echo("REVIEW SUMMARY")
        click.echo("=" * 70)
        click.echo(f"Total cases: {stats['total']}")
        click.echo(f"Accepted recommended: {stats['accepted']}")
        click.echo(f"Selected alternative: {stats['selected_different']}")
        click.echo(f"Skipped: {stats['skipped']}")
        click.echo()
        click.echo(f"Verified matches written to: {output_path}")
    else:
        click.echo()
        click.echo("No matches were verified.")


if __name__ == "__main__":
    main()

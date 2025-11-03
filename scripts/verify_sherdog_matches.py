#!/usr/bin/env python
"""Interactive CLI tool to verify Sherdog fighter matches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()


def load_matches() -> dict:
    """Load Sherdog matches from JSON file."""
    matches_file = Path("data/processed/sherdog_matches.json")

    if not matches_file.exists():
        console.print(f"[red]Error:[/red] Matches file not found: {matches_file}")
        console.print("Please run: make scrape-sherdog-search first")
        return {}

    with matches_file.open() as f:
        return json.load(f)


def load_existing_mapping() -> dict:
    """Load existing Sherdog ID mapping if it exists."""
    mapping_file = Path("data/sherdog_id_mapping.json")

    if mapping_file.exists():
        with mapping_file.open() as f:
            return json.load(f)

    return {}


def save_mapping(mapping: dict):
    """Save Sherdog ID mapping to JSON file."""
    mapping_file = Path("data/sherdog_id_mapping.json")
    mapping_file.parent.mkdir(parents=True, exist_ok=True)

    with mapping_file.open("w") as f:
        json.dump(mapping, f, indent=2)

    console.print(f"[green]✓[/green] Saved mapping to {mapping_file}")


def save_review_report(skipped_fighters: list[dict]):
    """Save report of fighters that need manual review.

    Args:
        skipped_fighters: List of fighters that were skipped
    """
    review_file = Path("data/sherdog_review_needed.json")
    review_file.parent.mkdir(parents=True, exist_ok=True)

    with review_file.open("w") as f:
        json.dump(skipped_fighters, f, indent=2)

    console.print(f"[yellow]⚠[/yellow] Saved {len(skipped_fighters)} fighters needing review to {review_file}")


def display_match(ufc_fighter: dict, sherdog_match: dict, confidence: float):
    """Display a match comparison in a formatted table."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Field", style="cyan", width=15)
    table.add_column("UFC Data", style="green", width=40)
    table.add_column("Sherdog Data", style="yellow", width=40)

    # Compare fields
    table.add_row("Name", ufc_fighter.get("name", ""), sherdog_match.get("name", ""))
    table.add_row("Division", ufc_fighter.get("division", ""), sherdog_match.get("division", ""))
    table.add_row("Record", ufc_fighter.get("record", ""), sherdog_match.get("record", ""))

    # Create panel with confidence score
    confidence_color = "green" if confidence >= 90 else "yellow" if confidence >= 60 else "red"
    title = f"[{confidence_color}]Confidence: {confidence}%[/{confidence_color}]"

    console.print(Panel(table, title=title, expand=False))

    if sherdog_match.get("sherdog_url"):
        console.print(f"Sherdog URL: [link]{sherdog_match['sherdog_url']}[/link]")


def verify_matches(matches: dict, mapping: dict, non_interactive: bool = False) -> dict:
    """Interactively verify ambiguous matches.

    Args:
        matches: Dict of UFC ID -> match data
        mapping: Existing Sherdog ID mapping
        non_interactive: If True, skip manual review and only auto-approve high confidence

    Returns:
        Updated mapping with user-verified matches
    """
    console.print("\n[bold cyan]Sherdog Fighter Match Verification[/bold cyan]\n")

    # Separate matches by confidence level
    # Adjust thresholds based on non_interactive mode
    high_threshold = 70 if non_interactive else 90
    low_threshold = 60

    high_confidence = []  # >= threshold
    needs_review = []     # between low and high threshold
    low_confidence = []   # < low_threshold
    skipped_for_review = []  # Fighters to review manually later

    for ufc_id, match_data in matches.items():
        ufc_fighter = match_data["ufc_fighter"]
        top_matches = match_data.get("matches", [])

        if not top_matches:
            low_confidence.append((ufc_id, ufc_fighter, None))
            continue

        best_match = top_matches[0]
        confidence = best_match["confidence"]

        if confidence >= high_threshold:
            high_confidence.append((ufc_id, ufc_fighter, best_match))
        elif confidence >= low_threshold:
            needs_review.append((ufc_id, ufc_fighter, top_matches))
        else:
            low_confidence.append((ufc_id, ufc_fighter, best_match))

    # Auto-approve high confidence matches
    console.print(f"[green]✓[/green] Auto-approving {len(high_confidence)} high-confidence matches (≥{high_threshold}%)")
    for ufc_id, ufc_fighter, match in high_confidence:
        if ufc_id not in mapping and match and match.get("sherdog_id"):
            mapping[ufc_id] = {
                "sherdog_id": match["sherdog_id"],
                "sherdog_url": match.get("sherdog_url"),
                "confidence": match["confidence"],
                "auto_approved": True,
            }

    # Skip low confidence matches
    console.print(f"[yellow]⚠[/yellow] Skipping {len(low_confidence)} low-confidence matches (<60%)")
    for ufc_id, ufc_fighter, _ in low_confidence:
        skipped_for_review.append({
            "ufc_id": ufc_id,
            "name": ufc_fighter["name"],
            "reason": "confidence < 60%",
        })

    # Manual review for ambiguous matches
    if non_interactive:
        console.print(f"[yellow]⚠[/yellow] Skipping {len(needs_review)} ambiguous matches ({low_threshold}-{high_threshold-1}% confidence) - non-interactive mode")
        for ufc_id, ufc_fighter, top_matches in needs_review:
            skipped_for_review.append({
                "ufc_id": ufc_id,
                "name": ufc_fighter["name"],
                "reason": f"confidence {low_threshold}-{high_threshold-1}%, needs manual review",
                "best_match": top_matches[0] if top_matches else None,
            })

        # Save skipped fighters for later review
        if skipped_for_review:
            save_review_report(skipped_for_review)

        return mapping

    console.print(f"\n[cyan]Review {len(needs_review)} ambiguous matches ({low_threshold}-{high_threshold-1}% confidence)[/cyan]\n")

    for idx, (ufc_id, ufc_fighter, top_matches) in enumerate(needs_review, 1):
        # Skip if already mapped
        if ufc_id in mapping:
            continue

        console.print(f"\n[bold]Match {idx}/{len(needs_review)}[/bold]")
        console.print(f"UFC Fighter: [green]{ufc_fighter['name']}[/green]\n")

        # Show all top matches
        for i, match in enumerate(top_matches, 1):
            console.print(f"\n[bold]Option {i}:[/bold]")
            display_match(ufc_fighter, match, match["confidence"])

        # Prompt for action
        console.print("\n[bold]Actions:[/bold]")
        console.print("  [green]1-3[/green] - Approve option 1, 2, or 3")
        console.print("  [yellow]s[/yellow] - Skip this match")
        console.print("  [red]q[/red] - Save and quit")

        choice = Prompt.ask(
            "\nYour choice",
            choices=["1", "2", "3", "s", "q"],
            default="s"
        )

        if choice == "q":
            console.print("\n[yellow]Saving and exiting...[/yellow]")
            break
        elif choice == "s":
            console.print("[yellow]Skipped[/yellow]")
            continue
        else:
            # Approve selected option
            option_idx = int(choice) - 1
            if option_idx < len(top_matches):
                selected = top_matches[option_idx]
                mapping[ufc_id] = {
                    "sherdog_id": selected["sherdog_id"],
                    "sherdog_url": selected.get("sherdog_url"),
                    "confidence": selected["confidence"],
                    "auto_approved": False,
                    "manually_verified": True,
                }
                console.print(f"[green]✓ Approved option {choice}[/green]")

    return mapping


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify Sherdog fighter matches")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (auto-approve ≥70%% confidence only)",
    )
    args = parser.parse_args()

    console.print("[bold cyan]Loading Sherdog matches...[/bold cyan]")

    matches = load_matches()
    if not matches:
        return

    mapping = load_existing_mapping()

    # Display summary
    console.print(f"Loaded {len(matches)} fighter matches")
    console.print(f"Existing mappings: {len(mapping)}")

    if args.non_interactive:
        console.print("[yellow]Running in non-interactive mode[/yellow]")

    # Run verification
    updated_mapping = verify_matches(matches, mapping, non_interactive=args.non_interactive)

    # Save results
    save_mapping(updated_mapping)

    console.print(f"\n[green]✓[/green] Verification complete!")
    console.print(f"Total mapped fighters: {len(updated_mapping)}")

    if args.non_interactive:
        review_file = Path("data/sherdog_review_needed.json")
        if review_file.exists():
            with review_file.open() as f:
                needs_review = json.load(f)
            console.print(f"[yellow]⚠[/yellow] {len(needs_review)} fighters need manual review (see {review_file})")


if __name__ == "__main__":
    main()

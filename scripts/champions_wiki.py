#!/usr/bin/env python
"""
Scrape UFC champion data from Wikipedia and update database with champion status.

This script:
1. Fetches the Wikipedia "List of UFC champions" page
2. Parses current and former champions by division
3. Matches Wikipedia names to database fighters using fuzzy matching
4. Updates database with champion status flags
5. Exports a CSV summary to data/champions_tags.csv
"""

from __future__ import annotations

import asyncio
import csv
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from sqlalchemy import select, update
from unidecode import unidecode

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.connection import get_session
from backend.db.models import Fighter
from scraper.utils.fuzzy_match import (
    calculate_match_confidence,
    normalize_division,
)

console = Console()

# Wikipedia URL for UFC champions
WIKIPEDIA_UFC_CHAMPIONS_URL = "https://en.wikipedia.org/wiki/List_of_UFC_champions"

# CSV output path
CSV_OUTPUT_PATH = Path("data/champions_tags.csv")

# Name alias map for known variants
NAME_ALIASES = {
    "josé aldo": "jose aldo",
    "joanna jędrzejczyk": "joanna jedrzejczyk",
    "joanna jedrzejczyk": "joanna jedrzejczyk",
    "cain velasquez": "cain velasquez",
    "fabricio werdum": "fabricio werdum",
    "junior dos santos": "junior dos santos",
    "júnior dos santos": "junior dos santos",
    "antônio rodrigo nogueira": "antonio rodrigo nogueira",
    "antonio rodrigo nogueira": "antonio rodrigo nogueira",
    "gabriel gonzaga": "gabriel gonzaga",
    "jon jones": "jon jones",
    "jonathan jones": "jon jones",
    "t.j. dillashaw": "tj dillashaw",
    "tj dillashaw": "tj dillashaw",
    "b.j. penn": "bj penn",
    "bj penn": "bj penn",
    "bas rutte": "bas rutten",
    "ricco rodriguez": "ricco rodriguez",
}


def normalize_fighter_name(name: str) -> str:
    """
    Normalize fighter name for comparison.

    Handles:
    - Lowercase conversion
    - Accent removal (José → Jose)
    - Jr., II, III suffix removal
    - Middle initial stripping
    - Extra whitespace normalization
    """
    # Remove accents
    name = unidecode(name)

    # Convert to lowercase
    name = name.lower().strip()

    # Remove suffixes (Jr., Sr., II, III, IV)
    name = re.sub(r'\s+(jr\.?|sr\.?|ii|iii|iv)$', '', name, flags=re.IGNORECASE)

    # Remove nicknames in quotes
    name = re.sub(r'"[^"]*"', '', name)

    # Normalize whitespace
    name = ' '.join(name.split())

    # Check alias map
    if name in NAME_ALIASES:
        return NAME_ALIASES[name]

    return name


def scrape_wikipedia_champions() -> dict[str, Any]:
    """
    Scrape current and former UFC champions from Wikipedia.

    Returns:
        Dict with structure:
        {
            'current_champions': [
                {'division': 'Heavyweight', 'name': 'Jon Jones', 'since': '2023-03-04'},
                ...
            ],
            'division_history': {
                'Heavyweight': [
                    {'name': 'Jon Jones', 'event': 'UFC 285', 'date': '2023-03-04',
                     'defenses': 0, 'interim': False},
                    ...
                ]
            }
        }
    """
    console.print("[bold cyan]Fetching Wikipedia UFC champions page...[/bold cyan]")

    # Fetch HTML with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(
                WIKIPEDIA_UFC_CHAMPIONS_URL,
                headers={'User-Agent': 'UFC-Pokedex-Scraper/1.0'},
                timeout=30
            )
            response.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                failure_message = (
                    f"[red]Failed to fetch Wikipedia after {max_retries} attempts: {e}[/red]"
                )
                console.print(failure_message)
                return {'current_champions': [], 'division_history': {}}
            retry_message = f"[yellow]Attempt {attempt + 1} failed, retrying...[/yellow]"
            console.print(retry_message)
            time.sleep(2)

    soup = BeautifulSoup(response.text, 'html.parser')

    current_champions = []
    division_history = {}

    # Parse current champions tables (first 2 tables are typically current champions)
    # Men's divisions (table 0) and Women's divisions (table 1)
    tables = soup.find_all('table', {'class': 'wikitable'})

    # First two tables are current champions (men + women)
    for table_idx in [0, 1]:
        if table_idx < len(tables):
            table = tables[table_idx]
            rows = table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:
                    division = cells[0].get_text(strip=True)
                    name_cell = cells[1]
                    # Extract just the name (remove footnotes, links, etc.)
                    name = name_cell.get_text(strip=True)
                    name = re.sub(r'\[.*?\]', '', name)  # Remove [1], [a], etc.
                    since = cells[2].get_text(strip=True) if len(cells) > 2 else None

                    current_champions.append({
                        'division': division,
                        'name': name,
                        'since': since
                    })

    # Parse division history tables
    # Each division has its own history table
    for table in tables:
        # Find the preceding heading to determine division
        heading = table.find_previous(['h2', 'h3', 'h4'])
        if heading:
            division_text = heading.get_text(strip=True)
            # Extract division name (e.g., "Heavyweight" from "Heavyweight Championship")
            division_match = re.search(r'(\w+(?:\s+\w+)?)\s+[Cc]hampionship', division_text)
            if division_match:
                division = division_match.group(1)

                history_entries = []
                rows = table.find_all('tr')[1:]  # Skip header

                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    # History tables have: No. | Name | Event | Date | Reign | Notes
                    # We want cell 1 (Name), not cell 0 (No.)
                    if len(cells) >= 2:
                        # Check if this is a history table (has numeric first cell)
                        first_cell = cells[0].get_text(strip=True)
                        is_history_table = first_cell.isdigit() or first_cell == 'No.'

                        if is_history_table and len(cells) >= 3:
                            # History table format: No. | Name | Event | Date | ...
                            name_cell = cells[1]  # Cell 1 is the Name column
                            event = cells[2].get_text(strip=True) if len(cells) > 2 else None
                            date_str = cells[3].get_text(strip=True) if len(cells) > 3 else None
                            defenses = '0'  # Not always available in history tables
                        else:
                            # Old format or different structure - skip
                            continue

                        name = name_cell.get_text(strip=True)
                        name = re.sub(r'\[.*?\]', '', name)  # Remove footnotes

                        # Extract just the champion's name (before "def." if present)
                        # Wikipedia tables sometimes include "Name def. Opponent" format
                        if 'def.' in name:
                            name = name.split('def.')[0].strip()

                        # Remove reign number indicators like "(2)" or "(3)"
                        name = re.sub(r'\(\d+\)$', '', name).strip()

                        # Remove "promoted to undisputed champion" suffix
                        name = re.sub(
                            r'promoted to undisputed champion.*$',
                            '',
                            name,
                            flags=re.IGNORECASE,
                        ).strip()

                        # Check for interim flag
                        is_interim = 'interim' in name.lower() or '†' in name
                        name = re.sub(r'\(interim\)', '', name, flags=re.IGNORECASE)
                        name = name.replace('†', '').strip()

                        # Parse defenses (could be "N/A", "0", "3", etc.)
                        try:
                            defenses = int(re.search(r'\d+', defenses).group()) if defenses else 0
                        except (AttributeError, ValueError):
                            defenses = 0

                        history_entries.append({
                            'name': name,
                            'event': event,
                            'date': date_str,
                            'defenses': defenses,
                            'interim': is_interim
                        })

                if history_entries:
                    division_history[division] = history_entries

    console.print(f"[green]✓[/green] Found {len(current_champions)} current champions")
    console.print(f"[green]✓[/green] Found history for {len(division_history)} divisions")

    return {
        'current_champions': current_champions,
        'division_history': division_history
    }


def build_champions_dataframe(champions_data: dict[str, Any]) -> pd.DataFrame:
    """
    Build a DataFrame from champions data.

    Columns:
    - fighter_name: Normalized name
    - division: Weight class
    - is_champion: Currently holds title
    - is_former_champion: Previously held title (not current)
    - was_interim: Ever held interim title
    - first_title_date: Date of first title win
    - last_title_date: Date of most recent title win
    - reign_count: Number of separate title reigns
    """
    rows = []

    # Build set of current champion names for quick lookup
    current_champ_names = {
        normalize_fighter_name(c['name'])
        for c in champions_data['current_champions']
    }

    # Process division history
    for division, history in champions_data['division_history'].items():
        # Group by fighter name
        fighter_reigns: dict[str, list[dict]] = {}
        for entry in history:
            norm_name = normalize_fighter_name(entry['name'])
            if norm_name not in fighter_reigns:
                fighter_reigns[norm_name] = []
            fighter_reigns[norm_name].append(entry)

        # Create row for each fighter
        for norm_name, reigns in fighter_reigns.items():
            is_current = norm_name in current_champ_names
            was_interim = any(r['interim'] for r in reigns)

            # Parse dates
            dates = []
            for reign in reigns:
                date_str = reign.get('date', '')
                if date_str:
                    try:
                        # Try parsing various date formats
                        date_obj = datetime.strptime(date_str, '%B %d, %Y')
                        dates.append(date_obj)
                    except ValueError:
                        try:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                            dates.append(date_obj)
                        except ValueError:
                            pass

            first_title_date = min(dates).strftime('%Y-%m-%d') if dates else None
            last_title_date = max(dates).strftime('%Y-%m-%d') if dates else None

            rows.append({
                'fighter_name': norm_name,
                'division': division,
                'is_champion': is_current,
                'is_former_champion': not is_current,  # If not current but in history
                'was_interim': was_interim,
                'first_title_date': first_title_date,
                'last_title_date': last_title_date,
                'reign_count': len(reigns)
            })

    df = pd.DataFrame(rows)

    # Deduplicate (some fighters might appear in multiple divisions)
    # Keep the most recent reign
    if not df.empty:
        df = df.sort_values('last_title_date', ascending=False)
        df = df.drop_duplicates(subset=['fighter_name'], keep='first')

    return df


async def match_to_database(champions_df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Match Wikipedia champion names to database fighters using fuzzy matching.

    Returns:
        List of matches with structure:
        [
            {
                'wikipedia_name': 'jon jones',
                'db_fighter_id': 'abc123',
                'db_fighter_name': 'Jon Jones',
                'confidence': 95.5,
                'is_champion': True,
                'is_former_champion': False,
                'championship_history': {...}
            },
            ...
        ]
    """
    console.print("\n[bold cyan]Matching champions to database fighters...[/bold cyan]")

    matches = []
    unmatched = []

    async with get_session() as session:
        # Load all fighters from database
        result = await session.execute(select(Fighter))
        db_fighters = result.scalars().all()

        console.print(f"Loaded {len(db_fighters)} fighters from database")

        # Match each Wikipedia champion
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                f"Matching {len(champions_df)} champions...",
                total=len(champions_df)
            )

            for _, row in champions_df.iterrows():
                wiki_name = row['fighter_name']
                division = row['division']

                best_match = None
                best_confidence = 0.0

                # Try exact match first
                for fighter in db_fighters:
                    db_name = normalize_fighter_name(fighter.name)

                    # Exact match
                    if db_name == wiki_name:
                        best_match = fighter
                        best_confidence = 100.0
                        break

                    # Fuzzy match
                    confidence = calculate_match_confidence(
                        {'name': wiki_name, 'division': normalize_division(division)},
                        {'name': db_name, 'division': normalize_division(fighter.division or '')}
                    )

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = fighter

                # Accept matches with confidence >= 90%
                if best_match and best_confidence >= 90.0:
                    matches.append({
                        'wikipedia_name': wiki_name,
                        'db_fighter_id': best_match.id,
                        'db_fighter_name': best_match.name,
                        'db_fighter_division': best_match.division,
                        'confidence': best_confidence,
                        'is_champion': row['is_champion'],
                        'is_former_champion': row['is_former_champion'],
                        'championship_history': {
                            'division': division,
                            'was_interim': row['was_interim'],
                            'first_title_date': row['first_title_date'],
                            'last_title_date': row['last_title_date'],
                            'reign_count': int(row['reign_count'])
                        }
                    })
                else:
                    unmatched.append({
                        'wikipedia_name': wiki_name,
                        'division': division,
                        'best_match': best_match.name if best_match else None,
                        'confidence': best_confidence
                    })

                progress.advance(task)

    console.print(f"\n[green]✓[/green] Matched {len(matches)} champions")

    if unmatched:
        console.print(f"\n[yellow]⚠[/yellow] {len(unmatched)} unmatched champions:")
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("Wikipedia Name", style="cyan")
        table.add_column("Division", style="magenta")
        table.add_column("Best Match", style="white")
        table.add_column("Confidence", style="yellow")

        for entry in unmatched[:10]:  # Show first 10
            table.add_row(
                entry['wikipedia_name'],
                entry['division'],
                entry['best_match'] or "None",
                f"{entry['confidence']:.1f}%"
            )

        console.print(table)

    return matches


async def update_database(matches: list[dict[str, Any]]) -> None:
    """Update database with champion status flags."""
    console.print("\n[bold cyan]Updating database...[/bold cyan]")

    async with get_session() as session:
        # First, reset all fighters to non-champion status
        await session.execute(
            update(Fighter).values(
                is_current_champion=False,
                is_former_champion=False,
                was_interim=False
            )
        )

        # Update matched fighters
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                f"Updating {len(matches)} fighters...",
                total=len(matches)
            )

            for match in matches:
                await session.execute(
                    update(Fighter)
                    .where(Fighter.id == match['db_fighter_id'])
                    .values(
                        is_current_champion=match['is_champion'],
                        is_former_champion=match['is_former_champion'],
                        was_interim=match['championship_history']['was_interim'],
                        championship_history=match['championship_history']
                    )
                )
                progress.advance(task)

        await session.commit()

    console.print("[green]✓[/green] Database updated successfully")


def export_csv(matches: list[dict[str, Any]]) -> None:
    """Export champion data to CSV."""
    console.print(f"\n[bold cyan]Exporting to {CSV_OUTPUT_PATH}...[/bold cyan]")

    # Ensure data directory exists
    CSV_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(CSV_OUTPUT_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'fighter_id',
            'fighter_name',
            'wikipedia_name',
            'division',
            'is_current_champion',
            'is_former_champion',
            'was_interim',
            'first_title_date',
            'last_title_date',
            'reign_count',
            'match_confidence'
        ])
        writer.writeheader()

        for match in matches:
            history = match['championship_history']
            writer.writerow({
                'fighter_id': match['db_fighter_id'],
                'fighter_name': match['db_fighter_name'],
                'wikipedia_name': match['wikipedia_name'],
                'division': history['division'],
                'is_current_champion': match['is_champion'],
                'is_former_champion': match['is_former_champion'],
                'was_interim': history['was_interim'],
                'first_title_date': history.get('first_title_date'),
                'last_title_date': history.get('last_title_date'),
                'reign_count': history['reign_count'],
                'match_confidence': f"{match['confidence']:.1f}%"
            })

    console.print(f"[green]✓[/green] CSV exported to {CSV_OUTPUT_PATH}")


async def main():
    """Main execution flow."""
    console.print("\n[bold cyan]═══ UFC Wikipedia Champions Scraper ═══[/bold cyan]\n")

    # Load environment
    load_dotenv()

    try:
        # 1. Scrape Wikipedia
        champions_data = scrape_wikipedia_champions()

        if not champions_data['current_champions'] and not champions_data['division_history']:
            console.print("[red]✗[/red] No champion data found. Check Wikipedia structure.")
            return

        # 2. Build DataFrame
        console.print("\n[bold cyan]Building champions dataframe...[/bold cyan]")
        champions_df = build_champions_dataframe(champions_data)
        console.print(f"[green]✓[/green] Built dataframe with {len(champions_df)} fighters")

        # 3. Match to database
        matches = await match_to_database(champions_df)

        if not matches:
            console.print("[red]✗[/red] No matches found. Database may be empty.")
            return

        # 4. Update database
        await update_database(matches)

        # 5. Export CSV
        export_csv(matches)

        # Summary
        console.print("\n[bold green]═══ Summary ═══[/bold green]")
        console.print(f"✓ Total champions processed: {len(champions_df)}")
        console.print(f"✓ Matched to database: {len(matches)}")
        console.print(f"✓ Current champions: {sum(1 for m in matches if m['is_champion'])}")
        console.print(f"✓ Former champions: {sum(1 for m in matches if m['is_former_champion'])}")
        console.print(f"✓ CSV exported: {CSV_OUTPUT_PATH}")
        console.print("\n[bold green]✓ Done![/bold green]\n")

    except (requests.exceptions.RequestException, OSError, ValueError, KeyError) as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise


if __name__ == "__main__":
    asyncio.run(main())

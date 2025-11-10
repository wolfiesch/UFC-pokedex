"""
Fight Matrix Historical Rankings Scraper

Scrapes top 50 fighters per division from Fight Matrix historical snapshots.
Uses BeautifulSoup4 for HTML parsing with resume capability.

Strategy:
- Phase 3A: Last 24 months (Nov 2023 - Nov 2025) - ~13 min, ~9,600 rankings
- Phase 3B: 2020-2023 (48 months) - ~26 min, ~19,200 rankings
- Phase 3C: 2008-2019 (144 months) - ~1.3 hours, ~57,600 rankings
- All: Complete archive (216 months) - ~2-3 hours, ~86,400 rankings

Usage:
    python scripts/scrape_fightmatrix_historical.py --phase 3A  # Recent 24 months
    python scripts/scrape_fightmatrix_historical.py --phase all  # All 216 months
    python scripts/scrape_fightmatrix_historical.py --months 6  # Custom month count
    python scripts/scrape_fightmatrix_historical.py --force  # Re-scrape existing files
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# Configuration
BASE_URL = "https://www.fightmatrix.com/historical-mma-rankings/ranking-snapshots/"
OUTPUT_DIR = Path("data/processed/fightmatrix_historical")
DIVISION_CODES_FILE = Path("data/processed/fightmatrix_division_codes.json")
ISSUE_MAPPING_FILE = Path("data/processed/fightmatrix_issue_mapping_complete.json")
DELAY_SECONDS = 2.0  # Respectful delay between requests
RETRY_ATTEMPTS = 3
RETRY_DELAY = 5

# Phase definitions (month ranges from most recent)
PHASE_DEFINITIONS = {
    '3A': {'months': 24, 'description': 'Last 24 months (Nov 2023 - Nov 2025)'},
    '3B': {'months': 72, 'description': '2020-2025 (72 months)'},
    '3C': {'months': 216, 'description': 'Complete archive (216 months, 2008-2025)'},
    'all': {'months': 216, 'description': 'Complete archive (216 months, 2008-2025)'},
}


def load_division_codes() -> Dict:
    """Load division codes from JSON file."""
    with open(DIVISION_CODES_FILE, 'r') as f:
        return json.load(f)


def load_issue_mapping() -> Dict:
    """Load complete issue mapping from JSON file."""
    with open(ISSUE_MAPPING_FILE, 'r') as f:
        return json.load(f)


def get_issues_for_phase(phase: str = None, months: int = None) -> List[Dict]:
    """
    Get issue list for specified phase or month count.

    Args:
        phase: Phase identifier ('3A', '3B', '3C', 'all')
        months: Custom month count (overrides phase)

    Returns:
        List of dicts with 'date' and 'issue' keys
    """
    mapping = load_issue_mapping()
    all_issues = mapping['issues']

    # Determine how many months to scrape
    if months is not None:
        count = months
        source = f"custom {months} months"
    elif phase and phase in PHASE_DEFINITIONS:
        count = PHASE_DEFINITIONS[phase]['months']
        source = f"Phase {phase} ({PHASE_DEFINITIONS[phase]['description']})"
    else:
        # Default to Phase 3A
        count = PHASE_DEFINITIONS['3A']['months']
        source = "Phase 3A (default)"

    # Get first N issues (most recent)
    issues = all_issues[:count]

    print(f"📋 Loading issues: {source}")
    print(f"   Total issues: {len(issues)}")
    print(f"   Date range: {issues[-1]['date']} to {issues[0]['date']}")
    print()

    return issues


def scrape_rankings_page(issue: int, division: int, page: int = 1) -> Optional[Dict]:
    """
    Scrape a single rankings page.

    Args:
        issue: Issue number (e.g., 996)
        division: Division code (e.g., 1 for Heavyweight)
        page: Page number (1-based, default 1)

    Returns:
        Dict with metadata and fighters list, or None if request fails
    """
    url = f"{BASE_URL}?Issue={issue}&Division={division}"
    if page > 1:
        url += f"&Page={page}"

    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find rankings table (second table on page)
            tables = soup.find_all('table')
            if len(tables) < 2:
                print(f"   ⚠️  No rankings table found")
                return None

            rankings_table = tables[1]

            # Extract fighters
            fighters = []
            tbody = rankings_table.find('tbody')
            if not tbody:
                print(f"   ⚠️  No tbody found in rankings table")
                return None

            rows = tbody.find_all('tr')
            # Skip header row if present
            if rows and rows[0].find('th'):
                rows = rows[1:]

            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 4:
                    continue

                rank_cell = cells[0]
                movement_cell = cells[1]
                fighter_cell = cells[2]
                points_cell = cells[3]

                # Extract fighter name and profile URL
                fighter_link = fighter_cell.find('a')
                if not fighter_link:
                    continue

                fighter_name = fighter_link.text.strip()
                profile_url = fighter_link.get('href', '')

                # Extract rank (handle ties)
                rank_text = rank_cell.text.strip()
                try:
                    rank = int(rank_text)
                except ValueError:
                    # Handle "T-5" style ties
                    rank = int(rank_text.replace('T-', ''))

                # Extract movement (↑1, ↓2, or empty)
                movement_text = movement_cell.text.strip()
                movement = None
                if movement_text and movement_text != '-':
                    movement = movement_text

                # Extract points
                points_text = points_cell.text.strip()
                try:
                    points = int(points_text)
                except ValueError:
                    points = 0

                fighters.append({
                    'rank': rank,
                    'name': fighter_name,
                    'profile_url': profile_url,
                    'points': points,
                    'movement': movement
                })

            # Get page title for verification
            page_title = soup.title.text if soup.title else ""

            return {
                'url': url,
                'issue': issue,
                'division': division,
                'page': page,
                'page_title': page_title,
                'fighter_count': len(fighters),
                'fighters': fighters,
                'scraped_at': datetime.utcnow().isoformat()
            }

        except requests.exceptions.Timeout:
            print(f"   ⏱️  Timeout on attempt {attempt + 1}/{RETRY_ATTEMPTS}")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY)
            else:
                print(f"   ❌ Failed after {RETRY_ATTEMPTS} attempts")
                return None

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None


def scrape_division_snapshot(issue: int, division: int, division_name: str,
                             max_pages: int = 2) -> Optional[Dict]:
    """
    Scrape top N fighters for a division in a specific issue.

    Args:
        issue: Issue number
        division: Division code
        division_name: Human-readable division name
        max_pages: Maximum pages to scrape (default 2 for top 50)

    Returns:
        Combined data from all pages, or None if failed
    """
    print(f"  📊 Scraping {division_name} (Division {division}, Issue {issue})")

    all_fighters = []

    for page_num in range(1, max_pages + 1):
        print(f"     Page {page_num}/{max_pages}...", end=" ")

        page_data = scrape_rankings_page(issue, division, page_num)

        if not page_data:
            print("FAILED")
            if page_num == 1:
                # First page failed, abort division
                return None
            else:
                # Subsequent page failed, maybe fewer than expected
                break

        all_fighters.extend(page_data['fighters'])
        print(f"✓ ({page_data['fighter_count']} fighters)")

        # Respectful delay between pages
        if page_num < max_pages:
            time.sleep(DELAY_SECONDS)

    if not all_fighters:
        return None

    return {
        'issue': issue,
        'division': division,
        'division_name': division_name,
        'total_fighters': len(all_fighters),
        'fighters': all_fighters,
        'scraped_at': datetime.utcnow().isoformat()
    }


def scrape_historical_rankings(phase: str = None,
                               months: int = None,
                               division_codes: Optional[List[int]] = None,
                               max_fighters: int = 50,
                               force: bool = False) -> None:
    """
    Main scraper function with resume capability.

    Args:
        phase: Phase identifier ('3A', '3B', '3C', 'all')
        months: Custom number of months (overrides phase)
        division_codes: Specific divisions to scrape (None = all major divisions)
        max_fighters: Max fighters per division (default 50 = 2 pages)
        force: Re-scrape existing files (default False)
    """
    print(f"🚀 Fight Matrix Historical Rankings Scraper")
    print(f"   Phase: {phase or 'custom'}")
    print(f"   Max fighters/division: {max_fighters}")
    print(f"   Force re-scrape: {force}")
    print()

    # Load division codes
    division_data = load_division_codes()

    # Default to major men's weight classes if not specified
    if division_codes is None:
        # Use main weight classes: HW, LHW, MW, WW, LW, FW, BW, FLW
        division_codes = [1, 2, 3, 4, 5, 6, 7, 8]

    # Get divisions info
    divisions_to_scrape = [
        d for d in division_data['divisions']
        if d['division_code'] in division_codes and d['category'] == 'weight_class'
    ]

    print(f"📋 Divisions to scrape:")
    for div in divisions_to_scrape:
        print(f"   - {div['division_name']} (Code: {div['division_code']})")
    print()

    # Calculate pages needed
    max_pages = (max_fighters + 24) // 25  # Round up to nearest 25

    # Get issues from mapping
    issues = get_issues_for_phase(phase, months)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Check for existing files (resume capability)
    existing_files = set()
    if not force:
        for file in OUTPUT_DIR.glob("issue_*.json"):
            existing_files.add(file.name)

        if existing_files:
            print(f"📂 Found {len(existing_files)} existing files")
            print(f"   Use --force to re-scrape them")
            print()

    # Filter issues to scrape
    issues_to_scrape = []
    issues_skipped = 0

    for issue_item in issues:
        issue_num = issue_item['issue']
        issue_date = issue_item['date']
        output_filename = f"issue_{issue_num}_{issue_date.replace('/', '-')}.json"

        if not force and output_filename in existing_files:
            issues_skipped += 1
            continue

        issues_to_scrape.append(issue_item)

    print(f"📊 Scrape summary:")
    print(f"   Total issues available: {len(issues)}")
    print(f"   Issues to scrape: {len(issues_to_scrape)}")
    print(f"   Issues skipped (existing): {issues_skipped}")
    print()

    if not issues_to_scrape:
        print(f"✅ All issues already scraped! Use --force to re-scrape.")
        return

    # Scrape each combination
    total_requests = len(divisions_to_scrape) * len(issues_to_scrape) * max_pages
    completed = 0

    print(f"📦 Starting scrape ({total_requests} total requests)")
    print()

    for issue_item in issues_to_scrape:
        issue_num = issue_item['issue']
        issue_date = issue_item['date']

        print(f"📅 Issue: {issue_date} (#{issue_num})")

        issue_results = {
            'issue_number': issue_num,
            'issue_date': issue_date,
            'divisions': []
        }

        for division in divisions_to_scrape:
            div_data = scrape_division_snapshot(
                issue_num,
                division['division_code'],
                division['division_name'],
                max_pages
            )

            if div_data:
                issue_results['divisions'].append(div_data)

            completed += max_pages
            progress = (completed / total_requests) * 100
            print(f"     Progress: {completed}/{total_requests} ({progress:.1f}%)")

            # Delay between divisions
            time.sleep(DELAY_SECONDS)

        # Save issue results
        output_file = OUTPUT_DIR / f"issue_{issue_num}_{issue_date.replace('/', '-')}.json"
        with open(output_file, 'w') as f:
            json.dump(issue_results, f, indent=2)

        print(f"  💾 Saved: {output_file.name}")
        print()

    print(f"✅ Scraping complete!")
    print(f"   Output directory: {OUTPUT_DIR}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Scrape Fight Matrix historical rankings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Phase options:
  3A    Last 24 months (Nov 2023 - Nov 2025) - ~13 min, ~9,600 rankings
  3B    2020-2025 (72 months) - ~39 min, ~28,800 rankings
  3C    2008-2025 (216 months) - ~2-3 hours, ~86,400 rankings
  all   Complete archive (same as 3C)

Examples:
  python scripts/scrape_fightmatrix_historical.py --phase 3A
  python scripts/scrape_fightmatrix_historical.py --phase all
  python scripts/scrape_fightmatrix_historical.py --months 6 --force
        """
    )

    parser.add_argument('--phase', type=str, default=None,
                       choices=['3A', '3B', '3C', 'all'],
                       help='Phase to execute (default: 3A)')
    parser.add_argument('--months', type=int, default=None,
                       help='Custom number of recent months (overrides --phase)')
    parser.add_argument('--divisions', type=str, default=None,
                       help='Comma-separated division codes (e.g., "1,5,7")')
    parser.add_argument('--max-fighters', type=int, default=50,
                       help='Max fighters per division (default: 50)')
    parser.add_argument('--force', action='store_true',
                       help='Re-scrape existing files')

    args = parser.parse_args()

    # Parse division codes
    division_codes = None
    if args.divisions:
        division_codes = [int(x.strip()) for x in args.divisions.split(',')]

    # Default to Phase 3A if neither phase nor months specified
    phase = args.phase if args.phase or args.months else '3A'

    scrape_historical_rankings(
        phase=phase,
        months=args.months,
        division_codes=division_codes,
        max_fighters=args.max_fighters,
        force=args.force
    )


if __name__ == "__main__":
    main()

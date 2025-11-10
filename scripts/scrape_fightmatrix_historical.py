"""
Fight Matrix Historical Rankings Scraper

Scrapes top 50 fighters per division from Fight Matrix historical snapshots.
Uses BeautifulSoup4 for HTML parsing (works with both requests and playwright).

Strategy:
- Target: Last 12 months of historical data
- Scope: Top 50 fighters per division (2 pages @ 25 fighters/page)
- Divisions: Focus on major weight classes (8 men's divisions)
- Total requests: ~192 pages (8 divisions × 12 months × 2 pages)

Usage:
    python scripts/scrape_fightmatrix_historical.py
    python scripts/scrape_fightmatrix_historical.py --months 6  # Last 6 months only
    python scripts/scrape_fightmatrix_historical.py --divisions 1,5,7  # Specific divisions
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
DELAY_SECONDS = 2.0  # Respectful delay between requests
RETRY_ATTEMPTS = 3
RETRY_DELAY = 5


def load_division_codes() -> Dict:
    """Load division codes from JSON file."""
    with open(DIVISION_CODES_FILE, 'r') as f:
        return json.load(f)


def get_latest_issues(count: int = 12) -> List[Dict]:
    """
    Fetch the latest N issue numbers from the dropdown.

    Returns:
        List of dicts with 'date' and 'issue_number' keys
    """
    print(f"🔍 Fetching latest {count} issue numbers...")

    try:
        response = requests.get(BASE_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the Issue dropdown (first select element)
        issue_select = soup.find_all('select')[0]
        if not issue_select:
            raise ValueError("Could not find Issue dropdown")

        # Extract issue options (skip "- Select Issue -")
        issues = []
        for option in issue_select.find_all('option')[1:count+1]:
            date_str = option.text.strip()
            # Issue number is extracted from URL or value attribute
            # For now, we'll need to test with known issue=996 and work backwards
            issues.append({
                'date': date_str,
                'issue_number': None,  # Will be filled in by testing
                'raw_option': option
            })

        print(f"✓ Found {len(issues)} recent issues")
        return issues

    except Exception as e:
        print(f"❌ Failed to fetch issue numbers: {e}")
        raise


def discover_issue_numbers(dates: List[str], test_division: int = 1) -> Dict[str, int]:
    """
    Discover issue numbers by testing sequential URLs.

    Strategy: Issue numbers appear to be sequential. We'll start from a known
    good issue (996 for 11/02/2025) and increment/decrement to find others.
    """
    print(f"🔍 Discovering issue numbers for {len(dates)} dates...")

    # Known reference point from testing
    KNOWN_DATE = "11/02/2025"
    KNOWN_ISSUE = 996

    date_to_issue = {}

    # Find the known date in our list
    if KNOWN_DATE in dates:
        known_index = dates.index(KNOWN_DATE)
        date_to_issue[KNOWN_DATE] = KNOWN_ISSUE

        # Work backwards from known issue
        for i in range(known_index + 1, len(dates)):
            issue_number = KNOWN_ISSUE - (i - known_index)
            date_to_issue[dates[i]] = issue_number

        # Work forwards from known issue
        for i in range(known_index - 1, -1, -1):
            issue_number = KNOWN_ISSUE + (known_index - i)
            date_to_issue[dates[i]] = issue_number
    else:
        # Fallback: assume sequential numbering from 996 backwards
        print(f"⚠️  Known date {KNOWN_DATE} not found, using fallback strategy")
        for i, date in enumerate(dates):
            date_to_issue[date] = KNOWN_ISSUE - i

    print(f"✓ Mapped {len(date_to_issue)} dates to issue numbers")
    return date_to_issue


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


def scrape_historical_rankings(months: int = 12,
                               division_codes: Optional[List[int]] = None,
                               max_fighters: int = 50) -> None:
    """
    Main scraper function.

    Args:
        months: Number of recent months to scrape
        division_codes: Specific divisions to scrape (None = all major divisions)
        max_fighters: Max fighters per division (default 50 = 2 pages)
    """
    print(f"🚀 Fight Matrix Historical Rankings Scraper")
    print(f"   Months: {months}")
    print(f"   Max fighters/division: {max_fighters}")
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

    # Get recent issue dates (will need issue numbers)
    print(f"🔍 Finding last {months} monthly snapshots...")
    # Hardcode recent dates based on reconnaissance
    recent_dates = [
        "11/02/2025", "10/05/2025", "09/07/2025", "08/03/2025",
        "07/06/2025", "06/01/2025", "05/04/2025", "04/06/2025",
        "03/02/2025", "02/02/2025", "01/05/2025", "12/01/2024"
    ][:months]

    # Map dates to issue numbers
    date_to_issue = discover_issue_numbers(recent_dates)

    print(f"✓ Found {len(date_to_issue)} issues to scrape")
    print()

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Scrape each combination
    total_requests = len(divisions_to_scrape) * len(date_to_issue) * max_pages
    completed = 0

    print(f"📦 Starting scrape ({total_requests} total requests)")
    print()

    for issue_date, issue_num in date_to_issue.items():
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
    parser = argparse.ArgumentParser(description='Scrape Fight Matrix historical rankings')
    parser.add_argument('--months', type=int, default=12,
                       help='Number of recent months to scrape (default: 12)')
    parser.add_argument('--divisions', type=str, default=None,
                       help='Comma-separated division codes (e.g., "1,5,7")')
    parser.add_argument('--max-fighters', type=int, default=50,
                       help='Max fighters per division (default: 50)')

    args = parser.parse_args()

    # Parse division codes
    division_codes = None
    if args.divisions:
        division_codes = [int(x.strip()) for x in args.divisions.split(',')]

    scrape_historical_rankings(
        months=args.months,
        division_codes=division_codes,
        max_fighters=args.max_fighters
    )


if __name__ == "__main__":
    main()

"""
Fight Matrix Division Code Mapper using Playwright

Purpose: Discover division numeric codes by testing each dropdown option with a real browser.
Output: Division name → Division code mapping (JSON)

Usage:
    PYTHONPATH=. .venv/bin/python scripts/map_fightmatrix_divisions.py
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


BASE_URL = "https://www.fightmatrix.com/historical-mma-rankings/ranking-snapshots/"
TEST_ISSUE = 996  # Known valid issue from reconnaissance
DELAY_SECONDS = 3  # Respectful delay between requests
OUTPUT_FILE = "data/processed/fightmatrix_division_codes.json"


def main():
    """Main entry point for division code mapping."""
    print(f"🔍 Starting Fight Matrix Division Code Mapper")
    print(f"   Base URL: {BASE_URL}")
    print(f"   Test Issue: {TEST_ISSUE}")
    print(f"   Delay: {DELAY_SECONDS}s between requests\n")

    # Ensure output directory exists
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        print("🌐 Launching browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Navigate to base page to get division list
            print(f"📄 Loading base page: {BASE_URL}")
            page.goto(BASE_URL, timeout=60000)
            time.sleep(2)  # Let page settle

            # Extract division dropdown options
            division_select = page.locator('select').nth(1)  # Second select is Division
            division_options = division_select.locator('option').all()

            divisions_to_test = []
            for option in division_options:
                text = option.text_content()
                if text and text.strip() and '- Select' not in text:
                    divisions_to_test.append(text.strip())

            print(f"✓ Found {len(divisions_to_test)} divisions to test\n")

            # Test each division
            results = []
            for division_code, division_name in enumerate(divisions_to_test, start=1):
                test_url = f"{BASE_URL}?Issue={TEST_ISSUE}&Division={division_code}"
                print(f"🧪 Testing Division {division_code}: {division_name}")
                print(f"   URL: {test_url}")

                try:
                    # Navigate to test URL
                    page.goto(test_url, timeout=60000)
                    time.sleep(2)  # Let page load

                    # Check if rankings table has data
                    tables = page.locator('table').all()
                    rankings_table = tables[1] if len(tables) > 1 else None

                    if rankings_table:
                        fighter_rows = rankings_table.locator('tbody tr').all()
                        has_data = len(fighter_rows) > 0
                        fighter_count = len(fighter_rows)
                    else:
                        has_data = False
                        fighter_count = 0

                    # Get page title for verification
                    page_title = page.title()

                    result = {
                        'division_name': division_name,
                        'division_code': division_code,
                        'verified': has_data,
                        'test_url': test_url,
                        'page_title': page_title,
                        'fighter_count': fighter_count
                    }

                    if has_data:
                        print(f"   ✓ VERIFIED: {fighter_count} fighters found")
                    else:
                        print(f"   ✗ NO DATA: Division might be invalid")

                    results.append(result)

                    # Respectful delay
                    if division_code < len(divisions_to_test):
                        print(f"   ⏳ Waiting {DELAY_SECONDS}s before next request...")
                        time.sleep(DELAY_SECONDS)
                    print()

                except PlaywrightTimeout:
                    print(f"   ✗ TIMEOUT: Could not load page")
                    results.append({
                        'division_name': division_name,
                        'division_code': division_code,
                        'verified': False,
                        'test_url': test_url,
                        'page_title': 'TIMEOUT',
                        'fighter_count': 0,
                        'error': 'Page load timeout'
                    })
                    print()
                except Exception as e:
                    print(f"   ✗ ERROR: {e}")
                    results.append({
                        'division_name': division_name,
                        'division_code': division_code,
                        'verified': False,
                        'test_url': test_url,
                        'page_title': 'ERROR',
                        'fighter_count': 0,
                        'error': str(e)
                    })
                    print()

            # Save results
            print(f"💾 Saving results to {OUTPUT_FILE}")
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(results, f, indent=2)

            # Print summary
            print(f"\n📊 Summary:")
            print(f"   Total divisions tested: {len(results)}")
            verified = [r for r in results if r['verified']]
            print(f"   Verified divisions: {len(verified)}")
            print(f"   Failed divisions: {len(results) - len(verified)}")

            print(f"\n✅ Verified Division Codes:")
            for r in verified:
                print(f"   {r['division_code']:2d} → {r['division_name']} ({r['fighter_count']} fighters)")

            if len(results) - len(verified) > 0:
                print(f"\n❌ Failed Division Codes:")
                for r in results:
                    if not r['verified']:
                        error_msg = r.get('error', 'No data found')
                        print(f"   {r['division_code']:2d} → {r['division_name']} ({error_msg})")

        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            raise
        finally:
            browser.close()
            print(f"\n🏁 Division mapping complete!")


if __name__ == "__main__":
    main()

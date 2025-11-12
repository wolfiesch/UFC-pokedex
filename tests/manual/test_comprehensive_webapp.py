"""
Comprehensive browser automation testing for UFC Pokedex
Tests all major user flows and captures bugs
"""
from playwright.sync_api import sync_playwright, Page, Browser
import json
import time

# Configuration
BASE_URL = "http://localhost:3000"
API_URL = "http://localhost:8000"
BUGS_FOUND = []

def log_bug(severity, category, description, screenshot_path=None):
    """Log a discovered bug"""
    bug = {
        "severity": severity,  # "critical", "high", "medium", "low"
        "category": category,
        "description": description,
        "screenshot": screenshot_path
    }
    BUGS_FOUND.append(bug)
    print(f"\n🐛 [{severity.upper()}] {category}: {description}")

def wait_and_check_console(page: Page, context: str):
    """Wait for page to settle and check for console errors"""
    console_errors = []

    def handle_console(msg):
        if msg.type in ['error', 'warning']:
            console_errors.append({
                'type': msg.type,
                'text': msg.text,
                'context': context
            })

    page.on('console', handle_console)
    page.wait_for_load_state('networkidle', timeout=10000)
    time.sleep(0.5)  # Extra settle time

    # Log any console errors found
    for error in console_errors:
        severity = "high" if error['type'] == 'error' else "medium"
        log_bug(severity, "Console Error", f"{error['context']}: {error['text']}")

    return console_errors

def test_home_page(page: Page):
    """Test home page loads and displays fighter list"""
    print("\n📋 Testing Home Page...")

    try:
        page.goto(BASE_URL, wait_until='networkidle')
        wait_and_check_console(page, "Home Page Load")

        # Take screenshot
        page.screenshot(path='/tmp/ufc_home.png', full_page=True)
        print("✅ Home page loaded")

        # Check for fighter cards
        fighter_cards = page.locator('[class*="FighterCard"], [class*="fighter-card"]').count()
        if fighter_cards == 0:
            log_bug("critical", "Home Page", "No fighter cards found on home page", '/tmp/ufc_home.png')
        else:
            print(f"✅ Found {fighter_cards} fighter cards")

        # Check for header/title
        title = page.title()
        print(f"✅ Page title: {title}")

        # Check for search input
        search_inputs = page.locator('input[type="text"], input[type="search"], input[placeholder*="search" i]').count()
        if search_inputs == 0:
            log_bug("medium", "Home Page", "No search input found")
        else:
            print(f"✅ Found search input")

        return True
    except Exception as e:
        log_bug("critical", "Home Page", f"Failed to load home page: {str(e)}")
        return False

def test_search_functionality(page: Page):
    """Test search with various queries"""
    print("\n🔍 Testing Search Functionality...")

    try:
        page.goto(BASE_URL, wait_until='networkidle')

        # Find search input
        search_input = page.locator('input[type="text"], input[type="search"], input[placeholder*="search" i]').first

        if not search_input.is_visible():
            log_bug("high", "Search", "Search input not visible")
            return False

        # Test 1: Search for common name
        print("Testing search for 'Silva'...")
        search_input.fill('Silva')
        page.wait_for_timeout(1000)  # Wait for debounce/search
        wait_and_check_console(page, "Search: Silva")

        page.screenshot(path='/tmp/ufc_search_silva.png', full_page=True)

        fighter_cards = page.locator('[class*="FighterCard"], [class*="fighter-card"]').count()
        if fighter_cards == 0:
            log_bug("medium", "Search", "No results for 'Silva' - should find fighters", '/tmp/ufc_search_silva.png')
        else:
            print(f"✅ Found {fighter_cards} results for 'Silva'")

        # Test 2: Search for non-existent fighter
        print("Testing search for 'XYZ123NonExistent'...")
        search_input.fill('XYZ123NonExistent')
        page.wait_for_timeout(1000)
        wait_and_check_console(page, "Search: Non-existent")

        page.screenshot(path='/tmp/ufc_search_empty.png', full_page=True)

        fighter_cards = page.locator('[class*="FighterCard"], [class*="fighter-card"]').count()
        no_results_msg = page.locator('text=/no.*results|not.*found/i').count()

        if fighter_cards > 0:
            log_bug("low", "Search", "Found results for non-existent fighter")
        elif no_results_msg == 0:
            log_bug("low", "Search", "No 'No results' message shown for empty search", '/tmp/ufc_search_empty.png')
        else:
            print("✅ Correctly shows no results message")

        # Test 3: Clear search
        search_input.fill('')
        page.wait_for_timeout(1000)
        fighter_cards = page.locator('[class*="FighterCard"], [class*="fighter-card"]').count()
        if fighter_cards == 0:
            log_bug("medium", "Search", "No fighters shown after clearing search")
        else:
            print(f"✅ Restored {fighter_cards} fighters after clearing search")

        return True
    except Exception as e:
        log_bug("high", "Search", f"Search functionality error: {str(e)}")
        return False

def test_fighter_detail_page(page: Page):
    """Test fighter detail page navigation and data display"""
    print("\n👤 Testing Fighter Detail Page...")

    try:
        page.goto(BASE_URL, wait_until='networkidle')

        # Find and click first fighter card
        fighter_card = page.locator('[class*="FighterCard"], [class*="fighter-card"], a[href*="/fighters/"]').first

        if not fighter_card.is_visible():
            log_bug("critical", "Fighter Detail", "No clickable fighter cards found")
            return False

        # Get fighter name before clicking
        fighter_name = fighter_card.locator('text=/[A-Z][a-z]+ [A-Z][a-z]+/').first.text_content() if fighter_card.locator('text=/[A-Z][a-z]+ [A-Z][a-z]+/').count() > 0 else "Unknown"
        print(f"Clicking fighter: {fighter_name}")

        fighter_card.click()
        page.wait_for_load_state('networkidle')
        wait_and_check_console(page, "Fighter Detail Page")

        page.screenshot(path='/tmp/ufc_fighter_detail.png', full_page=True)

        # Check if we're on a detail page
        current_url = page.url
        if '/fighters/' not in current_url:
            log_bug("critical", "Fighter Detail", f"Did not navigate to fighter detail page. URL: {current_url}", '/tmp/ufc_fighter_detail.png')
            return False

        print(f"✅ Navigated to: {current_url}")

        # Check for fighter data sections
        content = page.content()

        # Look for common fighter data
        has_record = 'record' in content.lower() or '-' in content  # e.g., "10-5-0"
        has_stats = any(stat in content.lower() for stat in ['height', 'weight', 'reach', 'stance', 'division'])

        if not has_stats:
            log_bug("high", "Fighter Detail", "Missing fighter stats (height, weight, reach, etc.)", '/tmp/ufc_fighter_detail.png')
        else:
            print("✅ Fighter stats present")

        # Check for back navigation
        back_button = page.locator('a[href="/"], button:has-text("back"), a:has-text("back")').count()
        if back_button == 0:
            log_bug("low", "Fighter Detail", "No back button or home link found")
        else:
            print("✅ Back navigation available")

        return True
    except Exception as e:
        log_bug("high", "Fighter Detail", f"Fighter detail page error: {str(e)}")
        return False

def test_favorites_functionality(page: Page):
    """Test favorites add, remove, and persistence"""
    print("\n⭐ Testing Favorites Functionality...")

    try:
        page.goto(BASE_URL, wait_until='networkidle')

        # Look for favorite buttons (heart icons, star icons, etc.)
        favorite_buttons = page.locator('button:has-text("♥"), button:has-text("★"), button[aria-label*="favorite" i], [class*="favorite"]').count()

        if favorite_buttons == 0:
            log_bug("medium", "Favorites", "No favorite buttons found")
            return False

        print(f"✅ Found {favorite_buttons} favorite buttons")

        # Click first favorite button
        first_fav = page.locator('button:has-text("♥"), button:has-text("★"), button[aria-label*="favorite" i], [class*="favorite"]').first
        first_fav.click()
        page.wait_for_timeout(500)

        page.screenshot(path='/tmp/ufc_favorites_add.png', full_page=True)

        # Check if favorites page/section exists
        favorites_link = page.locator('a[href*="favorite" i], button:has-text("Favorites")').count()
        if favorites_link > 0:
            page.locator('a[href*="favorite" i], button:has-text("Favorites")').first.click()
            page.wait_for_load_state('networkidle')
            wait_and_check_console(page, "Favorites Page")

            page.screenshot(path='/tmp/ufc_favorites_page.png', full_page=True)

            # Check if favorited fighter appears
            fighter_cards = page.locator('[class*="FighterCard"], [class*="fighter-card"]').count()
            if fighter_cards == 0:
                log_bug("medium", "Favorites", "No fighters shown on favorites page after adding", '/tmp/ufc_favorites_page.png')
            else:
                print(f"✅ Favorites page shows {fighter_cards} fighter(s)")
        else:
            log_bug("low", "Favorites", "No favorites page/section link found")

        return True
    except Exception as e:
        log_bug("medium", "Favorites", f"Favorites functionality error: {str(e)}")
        return False

def test_filters(page: Page):
    """Test stance and division filters"""
    print("\n🔧 Testing Filters...")

    try:
        page.goto(BASE_URL, wait_until='networkidle')

        # Look for filter dropdowns/buttons
        filter_elements = page.locator('select, button:has-text("Filter"), [class*="filter"]').count()

        if filter_elements == 0:
            log_bug("low", "Filters", "No filter elements found on home page")
            return False

        print(f"✅ Found {filter_elements} filter elements")

        # Try to interact with first filter
        first_filter = page.locator('select').first
        if first_filter.count() > 0 and first_filter.is_visible():
            # Get options
            options = first_filter.locator('option').count()
            print(f"✅ Filter has {options} options")

            # Select first non-default option
            if options > 1:
                first_filter.select_option(index=1)
                page.wait_for_timeout(1000)
                wait_and_check_console(page, "Filter Selection")

                page.screenshot(path='/tmp/ufc_filter_applied.png', full_page=True)

                fighter_cards = page.locator('[class*="FighterCard"], [class*="fighter-card"]').count()
                print(f"✅ After filter: {fighter_cards} fighters shown")

        return True
    except Exception as e:
        log_bug("low", "Filters", f"Filter functionality error: {str(e)}")
        return False

def test_responsive_design(page: Page):
    """Test responsive design at different breakpoints"""
    print("\n📱 Testing Responsive Design...")

    try:
        viewports = [
            {"width": 375, "height": 667, "name": "Mobile"},
            {"width": 768, "height": 1024, "name": "Tablet"},
            {"width": 1920, "height": 1080, "name": "Desktop"}
        ]

        for viewport in viewports:
            print(f"Testing {viewport['name']} ({viewport['width']}x{viewport['height']})...")
            page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
            page.goto(BASE_URL, wait_until='networkidle')
            page.wait_for_timeout(500)

            screenshot_path = f"/tmp/ufc_{viewport['name'].lower()}.png"
            page.screenshot(path=screenshot_path, full_page=False)

            # Check if content is visible
            fighter_cards = page.locator('[class*="FighterCard"], [class*="fighter-card"]').count()
            if fighter_cards == 0:
                log_bug("high", "Responsive", f"No fighter cards visible on {viewport['name']}", screenshot_path)
            else:
                print(f"✅ {viewport['name']}: {fighter_cards} cards visible")

        # Reset to desktop
        page.set_viewport_size({"width": 1920, "height": 1080})
        return True
    except Exception as e:
        log_bug("medium", "Responsive", f"Responsive design test error: {str(e)}")
        return False

def test_error_handling(page: Page):
    """Test error handling with invalid URLs"""
    print("\n❌ Testing Error Handling...")

    try:
        # Test invalid fighter ID
        invalid_urls = [
            f"{BASE_URL}/fighters/invalid-id-12345",
            f"{BASE_URL}/fighters/",
            f"{BASE_URL}/nonexistent-page"
        ]

        for url in invalid_urls:
            print(f"Testing: {url}")
            response = page.goto(url, wait_until='networkidle')
            wait_and_check_console(page, f"Error Page: {url}")

            screenshot_path = f"/tmp/ufc_error_{url.split('/')[-1]}.png"
            page.screenshot(path=screenshot_path, full_page=True)

            content = page.content()
            has_error_message = any(msg in content.lower() for msg in ['error', '404', 'not found', 'something went wrong'])

            if not has_error_message:
                log_bug("medium", "Error Handling", f"No error message shown for: {url}", screenshot_path)
            else:
                print(f"✅ Error message shown for {url}")

        return True
    except Exception as e:
        log_bug("medium", "Error Handling", f"Error handling test error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Comprehensive UFC Pokedex Testing\n")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Run all tests
        test_home_page(page)
        test_search_functionality(page)
        test_fighter_detail_page(page)
        test_favorites_functionality(page)
        test_filters(page)
        test_responsive_design(page)
        test_error_handling(page)

        browser.close()

    # Report findings
    print("\n" + "=" * 60)
    print("🏁 Testing Complete!")
    print("=" * 60)

    if len(BUGS_FOUND) == 0:
        print("\n✅ No bugs found! Application is working well.")
    else:
        print(f"\n🐛 Found {len(BUGS_FOUND)} issues:\n")

        # Group by severity
        by_severity = {}
        for bug in BUGS_FOUND:
            severity = bug['severity']
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(bug)

        for severity in ['critical', 'high', 'medium', 'low']:
            if severity in by_severity:
                print(f"\n{severity.upper()} ({len(by_severity[severity])}):")
                for i, bug in enumerate(by_severity[severity], 1):
                    print(f"  {i}. [{bug['category']}] {bug['description']}")
                    if bug['screenshot']:
                        print(f"     Screenshot: {bug['screenshot']}")

    # Save detailed report
    report_path = '/tmp/ufc_test_report.json'
    with open(report_path, 'w') as f:
        json.dump(BUGS_FOUND, f, indent=2)

    print(f"\n📄 Detailed report saved to: {report_path}")
    print("\nScreenshots saved to /tmp/ufc_*.png")

if __name__ == "__main__":
    main()

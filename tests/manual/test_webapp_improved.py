"""
Improved browser automation testing for UFC Pokedex
Uses better selectors and waits for dynamic React content
"""
from playwright.sync_api import sync_playwright, Page
import json
import time

BASE_URL = "http://localhost:3000"
BUGS_FOUND = []

def log_bug(severity, category, description, screenshot_path=None, extra_info=None):
    """Log a discovered bug"""
    bug = {
        "severity": severity,
        "category": category,
        "description": description,
        "screenshot": screenshot_path,
        "extra_info": extra_info
    }
    BUGS_FOUND.append(bug)
    print(f"\n🐛 [{severity.upper()}] {category}: {description}")
    if extra_info:
        print(f"   ℹ️  {extra_info}")

def wait_for_react_content(page: Page, timeout=10000):
    """Wait for React/Next.js dynamic content to load"""
    # Wait for network to be idle
    page.wait_for_load_state('networkidle', timeout=timeout)
    # Give React time to hydrate and render
    page.wait_for_timeout(2000)

def capture_console_errors(page: Page, context: str):
    """Capture console errors during page operations"""
    console_errors = []
    console_warnings = []

    def handle_console(msg):
        if msg.type == 'error':
            console_errors.append(f"{context}: {msg.text}")
        elif msg.type == 'warning':
            console_warnings.append(f"{context}: {msg.text}")

    page.on('console', handle_console)
    return console_errors, console_warnings

def test_home_page_detailed(page: Page):
    """Detailed home page inspection"""
    print("\n📋 Testing Home Page (Detailed)...")

    page.goto(BASE_URL)
    wait_for_react_content(page)

    page.screenshot(path='/tmp/ufc_home_detailed.png', full_page=True)

    # Check title
    title = page.title()
    print(f"✅ Page title: {title}")

    # Look for images (fighter photos)
    images = page.locator('img').count()
    print(f"Found {images} images on page")

    # Look for any article or card-like elements
    articles = page.locator('article').count()
    divs_with_links = page.locator('a[href*="/fighters/"]').count()
    print(f"Found {articles} article elements")
    print(f"Found {divs_with_links} links to fighter pages")

    if divs_with_links == 0:
        log_bug("critical", "Home Page", "No fighter links found - dynamic content may not be loading", '/tmp/ufc_home_detailed.png')
    else:
        print(f"✅ Found {divs_with_links} fighter links")

    # Check for search functionality
    search_input = page.locator('input[type="text"], input[placeholder*="Search" i]').count()
    print(f"Found {search_input} search input(s)")

    # Check for filters
    selects = page.locator('select').count()
    print(f"Found {selects} dropdown filters")

    # Capture network requests to see if API is being called
    print("\nChecking if API calls are being made...")

    return divs_with_links > 0

def test_search_with_wait(page: Page):
    """Test search with proper waiting for API response"""
    print("\n🔍 Testing Search (with API wait)...")

    page.goto(BASE_URL)
    wait_for_react_content(page)

    # Find search input
    search_input = page.locator('input[placeholder*="Search" i]').first

    if not search_input.is_visible():
        log_bug("high", "Search", "Search input not visible")
        return

    print("Searching for 'Anderson Silva'...")

    # Wait for response
    with page.expect_response("**/fighters/**") as response_info:
        search_input.fill('Anderson Silva')

    # Wait for content to update
    page.wait_for_timeout(2000)

    page.screenshot(path='/tmp/ufc_search_detailed.png', full_page=True)

    # Check for fighter links
    fighter_links = page.locator('a[href*="/fighters/"]').count()
    print(f"Found {fighter_links} fighter links after search")

    if fighter_links == 0:
        # Check for "no results" message
        content = page.content().lower()
        if 'no' in content and ('result' in content or 'found' in content):
            print("✅ Shows 'no results' message appropriately")
        else:
            log_bug("medium", "Search", "No results found for 'Anderson Silva' but no 'no results' message", '/tmp/ufc_search_detailed.png')

def test_fighter_detail_navigation(page: Page):
    """Test navigation to fighter detail page"""
    print("\n👤 Testing Fighter Detail Navigation...")

    page.goto(BASE_URL)
    wait_for_react_content(page)

    # Find first fighter link
    first_fighter_link = page.locator('a[href*="/fighters/"]').first

    if not first_fighter_link.is_visible():
        log_bug("critical", "Navigation", "No fighter links visible to click")
        return

    # Get href before clicking
    href = first_fighter_link.get_attribute('href')
    print(f"Clicking fighter link: {href}")

    first_fighter_link.click()
    wait_for_react_content(page)

    current_url = page.url
    print(f"Current URL: {current_url}")

    page.screenshot(path='/tmp/ufc_fighter_detail_fixed.png', full_page=True)

    if '/fighters/' not in current_url:
        log_bug("critical", "Navigation", f"Failed to navigate to fighter page. Expected path with /fighters/, got: {current_url}", '/tmp/ufc_fighter_detail_fixed.png')
    else:
        print(f"✅ Successfully navigated to fighter detail page")

        # Check for fighter data
        h1_count = page.locator('h1').count()
        img_count = page.locator('img').count()

        print(f"Detail page has {h1_count} h1 tags, {img_count} images")

        if h1_count == 0:
            log_bug("high", "Fighter Detail", "No fighter name heading (h1) found on detail page", '/tmp/ufc_fighter_detail_fixed.png')

def test_favorites_interaction(page: Page):
    """Test favorites button interaction"""
    print("\n⭐ Testing Favorites...")

    page.goto(BASE_URL)
    wait_for_react_content(page)

    # Look for heart/star buttons or favorite buttons
    favorite_buttons = page.locator('button[aria-label*="favorite" i], button[aria-label*="favourite" i]').count()
    heart_buttons = page.locator('button:has-text("♥"), button:has-text("❤")').count()

    print(f"Found {favorite_buttons} favorite buttons by aria-label")
    print(f"Found {heart_buttons} heart buttons by text")

    if favorite_buttons == 0 and heart_buttons == 0:
        log_bug("medium", "Favorites", "No favorite buttons found on fighter cards")
    else:
        print(f"✅ Found favorite buttons")

        # Try clicking one
        if favorite_buttons > 0:
            page.locator('button[aria-label*="favorite" i]').first.click()
        elif heart_buttons > 0:
            page.locator('button:has-text("♥")').first.click()

        page.wait_for_timeout(500)
        page.screenshot(path='/tmp/ufc_favorites_clicked.png', full_page=True)

def test_console_errors(page: Page):
    """Check for console errors across pages"""
    print("\n🔍 Testing Console Errors...")

    all_console_errors = []
    all_console_warnings = []

    def handle_console(msg):
        if msg.type == 'error':
            all_console_errors.append(msg.text)
        elif msg.type == 'warning':
            all_console_warnings.append(msg.text)

    page.on('console', handle_console)

    # Test home page
    print("Checking home page console...")
    page.goto(BASE_URL)
    wait_for_react_content(page)

    # Test fighter detail
    print("Checking fighter detail console...")
    first_fighter = page.locator('a[href*="/fighters/"]').first
    if first_fighter.is_visible():
        first_fighter.click()
        wait_for_react_content(page)

    # Report findings
    if len(all_console_errors) > 0:
        for error in all_console_errors[:5]:  # Limit to first 5
            log_bug("high", "Console Error", f"JavaScript error: {error[:200]}")

    if len(all_console_warnings) > 0:
        print(f"⚠️  Found {len(all_console_warnings)} console warnings")
        for warning in all_console_warnings[:3]:
            print(f"   - {warning[:150]}")

    if len(all_console_errors) == 0:
        print("✅ No console errors found")

def test_api_response_times(page: Page):
    """Test API response times"""
    print("\n⏱️  Testing API Response Times...")

    response_times = []

    def handle_response(response):
        if '/fighters' in response.url or '/search' in response.url:
            # Calculate time from request
            timing = response.request.timing
            if timing:
                duration = timing.get('responseEnd', 0) - timing.get('requestStart', 0)
                response_times.append({
                    'url': response.url,
                    'status': response.status,
                    'duration_ms': duration
                })
                print(f"  API call: {response.url} - {response.status} - {duration:.0f}ms")

    page.on('response', handle_response)

    page.goto(BASE_URL)
    wait_for_react_content(page)

    if len(response_times) == 0:
        log_bug("medium", "API", "No API calls detected - frontend may not be fetching data")
    else:
        avg_time = sum(r.get('duration_ms', 0) for r in response_times) / len(response_times)
        print(f"✅ Average API response time: {avg_time:.0f}ms")

        slow_responses = [r for r in response_times if r.get('duration_ms', 0) > 1000]
        if slow_responses:
            for slow in slow_responses:
                log_bug("low", "Performance", f"Slow API response: {slow['url']} took {slow['duration_ms']:.0f}ms")

def main():
    """Run improved test suite"""
    print("🚀 Starting Improved UFC Pokedex Testing")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        # Run tests
        test_home_page_detailed(page)
        test_search_with_wait(page)
        test_fighter_detail_navigation(page)
        test_favorites_interaction(page)
        test_api_response_times(page)
        test_console_errors(page)

        browser.close()

    # Report
    print("\n" + "=" * 60)
    print("🏁 Testing Complete!")
    print("=" * 60)

    if len(BUGS_FOUND) == 0:
        print("\n✅ No bugs found! Application is working well.")
    else:
        print(f"\n🐛 Found {len(BUGS_FOUND)} issues:\n")

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

    # Save report
    with open('/tmp/ufc_test_report_improved.json', 'w') as f:
        json.dump(BUGS_FOUND, f, indent=2)

    print(f"\n📄 Report: /tmp/ufc_test_report_improved.json")

if __name__ == "__main__":
    main()

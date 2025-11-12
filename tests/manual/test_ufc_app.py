#!/usr/bin/env python3
"""
Comprehensive Playwright test script for UFC Pokedex application.
This script tests main user flows and documents bugs with screenshots.
"""
import os
import json
from datetime import datetime
from playwright.sync_api import sync_playwright, Page

# Create output directory for screenshots and bug reports
OUTPUT_DIR = "/tmp/claude/ufc-pokedex-bug-investigation"
os.makedirs(OUTPUT_DIR, exist_ok=True)

bugs_found = []
test_results = []

def log_test(name, status, details="", screenshot_path=None):
    """Log test result"""
    result = {
        "test": name,
        "status": status,
        "details": details,
        "screenshot": screenshot_path,
        "timestamp": datetime.now().isoformat()
    }
    test_results.append(result)
    print(f"\n{'✅' if status == 'PASS' else '❌' if status == 'FAIL' else '⚠️'} {name}")
    if details:
        print(f"   {details}")

def log_bug(title, description, severity, screenshot_path=None, steps_to_reproduce=None):
    """Log a bug"""
    bug = {
        "title": title,
        "description": description,
        "severity": severity,  # CRITICAL, HIGH, MEDIUM, LOW
        "screenshot": screenshot_path,
        "steps_to_reproduce": steps_to_reproduce or [],
        "timestamp": datetime.now().isoformat()
    }
    bugs_found.append(bug)
    print(f"\n🐛 BUG FOUND: {title}")
    print(f"   Severity: {severity}")
    print(f"   {description}")

def take_screenshot(page: Page, name: str) -> str:
    """Take a screenshot and return the path"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{name}.png"
    path = os.path.join(OUTPUT_DIR, filename)
    page.screenshot(path=path, full_page=True)
    return path

def test_home_page(page: Page):
    """Test home page load and initial state"""
    print("\n" + "="*60)
    print("TEST: Home Page")
    print("="*60)

    try:
        page.goto('http://localhost:3000')
        page.wait_for_load_state('networkidle')

        # Take initial screenshot
        screenshot = take_screenshot(page, "home_page_initial")

        # Check title
        title = page.title()
        if "UFC" in title or "Fighter" in title or "Pokedex" in title:
            log_test("Home page title", "PASS", f"Title: {title}", screenshot)
        else:
            log_test("Home page title", "WARN", f"Unexpected title: {title}", screenshot)

        # Check for main heading
        headings = page.locator('h1').all_text_contents()
        log_test("Main heading present", "PASS" if headings else "FAIL",
                f"Headings: {headings}", screenshot)

        # Check if fighter cards are loaded
        fighter_cards = page.locator('[class*="card"]').count()
        if fighter_cards > 0:
            log_test("Fighter cards loaded", "PASS",
                    f"Found {fighter_cards} fighter cards", screenshot)
        else:
            # Try alternative selectors
            links = page.locator('a[href*="/fighters/"]').count()
            if links > 0:
                log_test("Fighter links loaded", "PASS",
                        f"Found {links} fighter links", screenshot)
            else:
                log_test("Fighter cards/links loaded", "FAIL",
                        "No fighter cards or links found", screenshot)
                log_bug(
                    "No fighter data on home page",
                    "Home page loads but no fighter cards or links are visible",
                    "CRITICAL",
                    screenshot,
                    ["Navigate to http://localhost:3000", "Wait for page load", "Observe empty page"]
                )

        # Check for search functionality
        search_inputs = page.locator('input[type="search"], input[type="text"][placeholder*="search" i]').count()
        log_test("Search input present", "PASS" if search_inputs > 0 else "WARN",
                f"Found {search_inputs} search inputs", screenshot)

        # Check console for errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    except Exception as e:
        screenshot = take_screenshot(page, "home_page_error")
        log_test("Home page load", "FAIL", f"Error: {str(e)}", screenshot)
        log_bug(
            "Home page failed to load",
            f"Exception occurred: {str(e)}",
            "CRITICAL",
            screenshot,
            ["Navigate to http://localhost:3000", "Page crashes or fails to load"]
        )

def test_search_functionality(page: Page):
    """Test search functionality"""
    print("\n" + "="*60)
    print("TEST: Search Functionality")
    print("="*60)

    try:
        # Look for search input
        search_selectors = [
            'input[type="search"]',
            'input[type="text"][placeholder*="search" i]',
            'input[placeholder*="fighter" i]',
            'input[name*="search" i]'
        ]

        search_input = None
        for selector in search_selectors:
            if page.locator(selector).count() > 0:
                search_input = page.locator(selector).first
                break

        if not search_input:
            screenshot = take_screenshot(page, "search_no_input")
            log_test("Search input found", "FAIL", "No search input found", screenshot)
            log_bug(
                "Search input not found",
                "Cannot locate search input on home page using common selectors",
                "HIGH",
                screenshot
            )
            return

        # Test search with a common name
        search_input.fill("silva")
        page.wait_for_timeout(1000)  # Wait for debounce/results

        screenshot = take_screenshot(page, "search_silva_results")

        # Check if results updated
        fighter_count_after = page.locator('a[href*="/fighters/"]').count()
        log_test("Search filters results", "PASS" if fighter_count_after > 0 else "WARN",
                f"Found {fighter_count_after} results for 'silva'", screenshot)

        # Clear search
        search_input.clear()
        page.wait_for_timeout(1000)

    except Exception as e:
        screenshot = take_screenshot(page, "search_error")
        log_test("Search functionality", "FAIL", f"Error: {str(e)}", screenshot)

def test_fighter_detail_page(page: Page):
    """Test fighter detail page"""
    print("\n" + "="*60)
    print("TEST: Fighter Detail Page")
    print("="*60)

    try:
        # Find first fighter link
        fighter_links = page.locator('a[href*="/fighters/"]')

        if fighter_links.count() == 0:
            screenshot = take_screenshot(page, "no_fighter_links")
            log_test("Fighter links available", "FAIL", "No fighter links found", screenshot)
            return

        # Get the first fighter link
        first_link = fighter_links.first
        fighter_name = first_link.text_content().strip()
        fighter_url = first_link.get_attribute('href')

        print(f"   Testing fighter: {fighter_name}")
        print(f"   URL: {fighter_url}")

        # Click and navigate
        first_link.click()
        page.wait_for_load_state('networkidle')

        screenshot = take_screenshot(page, f"fighter_detail_{fighter_name.replace(' ', '_')}")

        # Check URL changed
        current_url = page.url
        if "/fighters/" in current_url:
            log_test("Navigation to fighter detail", "PASS",
                    f"URL: {current_url}", screenshot)
        else:
            log_test("Navigation to fighter detail", "FAIL",
                    f"Unexpected URL: {current_url}", screenshot)
            log_bug(
                "Fighter detail navigation failed",
                f"Clicked fighter link but URL didn't change to fighter detail page. Current URL: {current_url}",
                "HIGH",
                screenshot
            )
            return

        # Check for fighter name on page
        page_text = page.locator('body').text_content()
        if fighter_name.lower() in page_text.lower():
            log_test("Fighter name displayed", "PASS", screenshot=screenshot)
        else:
            log_test("Fighter name displayed", "WARN",
                    f"Fighter name '{fighter_name}' not found on detail page", screenshot)

        # Check for stats/info sections
        headings = page.locator('h2, h3').all_text_contents()
        log_test("Info sections present", "PASS" if len(headings) > 0 else "WARN",
                f"Found {len(headings)} section headings", screenshot)

        # Check for back navigation
        back_buttons = page.locator('a[href="/"], button:has-text("back" i), a:has-text("back" i)').count()
        log_test("Back navigation present", "PASS" if back_buttons > 0 else "WARN",
                f"Found {back_buttons} back buttons/links", screenshot)

        # Check for 404 or error messages
        error_keywords = ["404", "not found", "error", "failed to load"]
        has_error = any(keyword in page_text.lower() for keyword in error_keywords)
        if has_error:
            log_test("No error messages", "FAIL", "Error message detected on page", screenshot)
            log_bug(
                "Error on fighter detail page",
                f"Fighter detail page for {fighter_name} shows error message",
                "HIGH",
                screenshot,
                [f"Navigate to {fighter_url}", "Observe error message"]
            )
        else:
            log_test("No error messages", "PASS", screenshot=screenshot)

    except Exception as e:
        screenshot = take_screenshot(page, "fighter_detail_error")
        log_test("Fighter detail page", "FAIL", f"Error: {str(e)}", screenshot)

def test_favorites_functionality(page: Page):
    """Test favorites functionality"""
    print("\n" + "="*60)
    print("TEST: Favorites Functionality")
    print("="*60)

    try:
        # Go back to home
        page.goto('http://localhost:3000')
        page.wait_for_load_state('networkidle')

        # Look for favorite buttons (stars, hearts, etc.)
        favorite_selectors = [
            'button[aria-label*="favorite" i]',
            'button[aria-label*="add to favorites" i]',
            'button:has-text("★")',
            'button:has-text("☆")',
            '[class*="favorite"]'
        ]

        favorite_button = None
        for selector in favorite_selectors:
            if page.locator(selector).count() > 0:
                favorite_button = page.locator(selector).first
                break

        if not favorite_button:
            screenshot = take_screenshot(page, "favorites_no_button")
            log_test("Favorite button found", "WARN",
                    "No favorite buttons found on home page", screenshot)
            return

        # Click favorite button
        favorite_button.click()
        page.wait_for_timeout(500)

        screenshot = take_screenshot(page, "favorite_added")
        log_test("Favorite toggle interaction", "PASS",
                "Favorite button clicked successfully", screenshot)

        # Look for favorites page link
        favorites_link = page.locator('a[href*="favorite" i]').first
        if favorites_link.count() > 0:
            favorites_link.click()
            page.wait_for_load_state('networkidle')

            screenshot = take_screenshot(page, "favorites_page")

            # Check if we're on favorites page
            current_url = page.url
            if "favorite" in current_url.lower():
                log_test("Navigate to favorites page", "PASS",
                        f"URL: {current_url}", screenshot)
            else:
                log_test("Navigate to favorites page", "WARN",
                        f"URL doesn't contain 'favorite': {current_url}", screenshot)
        else:
            screenshot = take_screenshot(page, "no_favorites_link")
            log_test("Favorites page link found", "WARN",
                    "No link to favorites page found", screenshot)

    except Exception as e:
        screenshot = take_screenshot(page, "favorites_error")
        log_test("Favorites functionality", "FAIL", f"Error: {str(e)}", screenshot)

def test_responsive_design(page: Page):
    """Test responsive design at different viewport sizes"""
    print("\n" + "="*60)
    print("TEST: Responsive Design")
    print("="*60)

    viewports = [
        {"width": 375, "height": 667, "name": "mobile"},
        {"width": 768, "height": 1024, "name": "tablet"},
        {"width": 1920, "height": 1080, "name": "desktop"}
    ]

    try:
        page.goto('http://localhost:3000')

        for viewport in viewports:
            page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
            page.wait_for_timeout(500)

            screenshot = take_screenshot(page, f"responsive_{viewport['name']}")

            # Check if content is visible
            body_width = page.evaluate("document.body.scrollWidth")
            viewport_width = viewport["width"]

            if body_width > viewport_width * 1.1:  # Allow 10% overflow
                log_test(f"Responsive {viewport['name']}", "WARN",
                        f"Horizontal overflow detected: body={body_width}px, viewport={viewport_width}px",
                        screenshot)
                log_bug(
                    f"Horizontal overflow on {viewport['name']} viewport",
                    f"Page content ({body_width}px) exceeds viewport width ({viewport_width}px)",
                    "MEDIUM",
                    screenshot,
                    [f"Set viewport to {viewport['width']}x{viewport['height']}",
                     "Navigate to home page", "Observe horizontal scrollbar"]
                )
            else:
                log_test(f"Responsive {viewport['name']}", "PASS",
                        f"No horizontal overflow", screenshot)

        # Reset viewport
        page.set_viewport_size({"width": 1280, "height": 720})

    except Exception as e:
        screenshot = take_screenshot(page, "responsive_error")
        log_test("Responsive design", "FAIL", f"Error: {str(e)}", screenshot)

def test_console_and_network_errors(page: Page):
    """Check for console errors and failed network requests"""
    print("\n" + "="*60)
    print("TEST: Console & Network Errors")
    print("="*60)

    console_messages = []
    failed_requests = []

    # Capture console messages
    page.on("console", lambda msg: console_messages.append({
        "type": msg.type,
        "text": msg.text
    }))

    # Capture failed requests
    page.on("response", lambda response: failed_requests.append({
        "url": response.url,
        "status": response.status
    }) if response.status >= 400 else None)

    try:
        # Navigate and perform some interactions
        page.goto('http://localhost:3000')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)

        # Check console errors
        errors = [msg for msg in console_messages if msg["type"] == "error"]
        if errors:
            log_test("Console errors", "FAIL", f"Found {len(errors)} console errors")
            for error in errors[:5]:  # Log first 5
                print(f"   - {error['text']}")
                log_bug(
                    f"Console error: {error['text'][:100]}",
                    f"Console error detected: {error['text']}",
                    "MEDIUM",
                    steps_to_reproduce=["Open browser console", "Navigate to home page", "Observe error"]
                )
        else:
            log_test("Console errors", "PASS", "No console errors detected")

        # Check failed requests
        if failed_requests:
            log_test("Network requests", "FAIL", f"Found {len(failed_requests)} failed requests")
            for req in failed_requests[:5]:  # Log first 5
                print(f"   - {req['status']} {req['url']}")
                log_bug(
                    f"Failed network request: {req['status']} {req['url'][:100]}",
                    f"HTTP {req['status']} error for: {req['url']}",
                    "HIGH" if req['status'] >= 500 else "MEDIUM",
                    steps_to_reproduce=["Open network tab", "Navigate to page", f"Observe {req['status']} response"]
                )
        else:
            log_test("Network requests", "PASS", "All network requests successful")

    except Exception as e:
        log_test("Console & Network check", "FAIL", f"Error: {str(e)}")

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("UFC POKEDEX - BUG INVESTIGATION WITH PLAYWRIGHT")
    print("="*70)
    print(f"Output directory: {OUTPUT_DIR}")
    print("="*70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        # Run all tests
        test_home_page(page)
        test_search_functionality(page)
        test_fighter_detail_page(page)
        test_favorites_functionality(page)
        test_responsive_design(page)
        test_console_and_network_errors(page)

        browser.close()

    # Generate reports
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    total_tests = len(test_results)
    passed = len([t for t in test_results if t["status"] == "PASS"])
    failed = len([t for t in test_results if t["status"] == "FAIL"])
    warnings = len([t for t in test_results if t["status"] == "WARN"])

    print(f"\nTotal tests: {total_tests}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Warnings: {warnings}")

    print("\n" + "="*70)
    print(f"BUGS FOUND: {len(bugs_found)}")
    print("="*70)

    if bugs_found:
        # Group by severity
        critical = [b for b in bugs_found if b["severity"] == "CRITICAL"]
        high = [b for b in bugs_found if b["severity"] == "HIGH"]
        medium = [b for b in bugs_found if b["severity"] == "MEDIUM"]
        low = [b for b in bugs_found if b["severity"] == "LOW"]

        print(f"\n🔴 CRITICAL: {len(critical)}")
        for bug in critical:
            print(f"   - {bug['title']}")

        print(f"\n🟠 HIGH: {len(high)}")
        for bug in high:
            print(f"   - {bug['title']}")

        print(f"\n🟡 MEDIUM: {len(medium)}")
        for bug in medium:
            print(f"   - {bug['title']}")

        print(f"\n🟢 LOW: {len(low)}")
        for bug in low:
            print(f"   - {bug['title']}")
    else:
        print("\n🎉 No bugs found!")

    # Save reports to JSON
    report = {
        "summary": {
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "bugs_found": len(bugs_found)
        },
        "test_results": test_results,
        "bugs": bugs_found,
        "timestamp": datetime.now().isoformat()
    }

    report_path = os.path.join(OUTPUT_DIR, "bug_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Detailed report saved to: {report_path}")
    print(f"📸 Screenshots saved to: {OUTPUT_DIR}")
    print("\n" + "="*70)

if __name__ == "__main__":
    main()

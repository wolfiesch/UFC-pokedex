#!/usr/bin/env python3
"""
UFC Pokedex Frontend-Only Test
Tests the frontend in isolation (may show loading states or errors if no backend)
"""
from playwright.sync_api import sync_playwright
import time

def test_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        print("=" * 60)
        print("UFC Pokedex Frontend Test (No Backend)")
        print("=" * 60)

        # Navigate to frontend
        print("\n[Test 1] Loading frontend page...")
        page.goto('http://localhost:3000')
        page.wait_for_load_state('networkidle')
        time.sleep(3)  # Extra wait for any API calls to fail gracefully

        # Take screenshot
        page.screenshot(path='/tmp/ufc_frontend_only.png', full_page=True)
        print("✓ Frontend loaded")
        print("  Screenshot saved: /tmp/ufc_frontend_only.png")

        # Check page title
        title = page.title()
        print(f"  Page title: {title}")

        # Discover elements
        print("\n[Test 2] Discovering page structure...")

        # Check for loading states
        loading = page.locator('[class*="loading"], [role="status"]').all()
        print(f"  - Loading indicators: {len(loading)}")

        # Check for error messages
        errors = page.locator('[class*="error"], [role="alert"]').all()
        print(f"  - Error messages: {len(errors)}")

        # Check navigation
        nav_links = page.locator('nav a, header a').all()
        print(f"  - Navigation links: {len(nav_links)}")
        for i, link in enumerate(nav_links[:5]):
            try:
                text = link.inner_text().strip()
                href = link.get_attribute('href')
                print(f"    [{i}] {text} → {href}")
            except:
                pass

        # Check for buttons
        buttons = page.locator('button').all()
        print(f"  - Buttons: {len(buttons)}")

        # Console messages
        print("\n[Test 3] Console messages...")
        console_messages = []

        def handle_console(msg):
            console_messages.append({'type': msg.type, 'text': msg.text})

        page.on('console', handle_console)
        page.reload()
        page.wait_for_load_state('networkidle')
        time.sleep(2)

        errors_console = [m for m in console_messages if m['type'] == 'error']
        print(f"  - Console errors: {len(errors_console)}")
        for error in errors_console[:5]:
            print(f"    ERROR: {error['text'][:100]}")

        # Network requests
        print("\n[Test 4] Network activity...")
        requests = []

        def handle_request(request):
            requests.append({
                'method': request.method,
                'url': request.url,
                'type': request.resource_type
            })

        page.on('request', handle_request)
        page.reload()
        page.wait_for_load_state('networkidle')
        time.sleep(2)

        api_requests = [r for r in requests if 'localhost:8000' in r['url'] or '/api/' in r['url']]
        print(f"  - Total requests: {len(requests)}")
        print(f"  - API requests: {len(api_requests)}")
        for req in api_requests[:5]:
            print(f"    {req['method']} {req['url']}")

        print("\n" + "=" * 60)
        print("Frontend Test Complete")
        print("=" * 60)
        print("✓ Frontend is accessible")
        print(f"✓ Console errors: {len(errors_console)}")
        print(f"✓ API requests attempted: {len(api_requests)}")
        print("=" * 60)

        browser.close()

if __name__ == '__main__':
    test_frontend()

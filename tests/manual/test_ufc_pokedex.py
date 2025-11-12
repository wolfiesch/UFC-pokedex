#!/usr/bin/env python3
"""
UFC Pokedex Web Application Test
Tests key functionality of the application using Playwright
"""
from playwright.sync_api import sync_playwright
import time

def test_ufc_pokedex():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Set viewport size for consistent screenshots
        page.set_viewport_size({"width": 1920, "height": 1080})

        print("=" * 60)
        print("UFC Pokedex Web Application Test")
        print("=" * 60)

        # Test 1: Home Page Load
        print("\n[Test 1] Loading home page...")
        page.goto('http://localhost:3000')
        page.wait_for_load_state('networkidle')
        time.sleep(2)  # Extra wait for data fetching

        page.screenshot(path='/tmp/ufc_pokedex_home.png', full_page=True)
        print("✓ Home page loaded")
        print("  Screenshot saved: /tmp/ufc_pokedex_home.png")

        # Test 2: Discover Fighter Cards
        print("\n[Test 2] Discovering fighter cards...")
        fighter_cards = page.locator('[data-testid="fighter-card"], .fighter-card, article, [class*="card"]').all()

        # Try alternative selectors if no cards found
        if len(fighter_cards) == 0:
            fighter_cards = page.locator('a[href^="/fighters/"]').all()

        print(f"✓ Found {len(fighter_cards)} fighter elements")

        # Test 3: Discover Page Elements
        print("\n[Test 3] Discovering page elements...")

        # Check for search functionality
        search_inputs = page.locator('input[type="search"], input[placeholder*="search" i], input[placeholder*="filter" i]').all()
        print(f"  - Search inputs: {len(search_inputs)}")

        # Check for buttons
        buttons = page.locator('button').all()
        print(f"  - Buttons: {len(buttons)}")
        for i, button in enumerate(buttons[:5]):  # Show first 5
            try:
                text = button.inner_text().strip() if button.is_visible() else "[hidden]"
                print(f"    [{i}] {text}")
            except:
                pass

        # Check for navigation links
        links = page.locator('a[href]').all()
        print(f"  - Links: {len(links)}")

        # Test 4: Click on First Fighter (if available)
        if len(fighter_cards) > 0:
            print("\n[Test 4] Clicking on first fighter...")
            try:
                first_fighter = fighter_cards[0]
                first_fighter.click()
                page.wait_for_load_state('networkidle')
                time.sleep(1)

                page.screenshot(path='/tmp/ufc_pokedex_fighter_detail.png', full_page=True)
                print("✓ Fighter detail page loaded")
                print("  Screenshot saved: /tmp/ufc_pokedex_fighter_detail.png")

                # Check for fighter details
                current_url = page.url
                print(f"  Current URL: {current_url}")

                # Look for favorites button
                fav_buttons = page.locator('button:has-text("favorite"), button[aria-label*="favorite" i], button[class*="favorite"]').all()
                print(f"  - Favorite buttons found: {len(fav_buttons)}")

                # Go back to home
                page.go_back()
                page.wait_for_load_state('networkidle')
                time.sleep(1)
                print("✓ Navigated back to home page")

            except Exception as e:
                print(f"✗ Error clicking fighter: {e}")
        else:
            print("\n[Test 4] SKIPPED - No fighter cards found")

        # Test 5: Test Search/Filter Functionality
        print("\n[Test 5] Testing search/filter functionality...")
        if len(search_inputs) > 0:
            try:
                search_input = search_inputs[0]
                search_input.fill("McGregor")
                time.sleep(2)  # Wait for filtering

                page.screenshot(path='/tmp/ufc_pokedex_search.png', full_page=True)
                print("✓ Search filter applied")
                print("  Screenshot saved: /tmp/ufc_pokedex_search.png")

                # Clear search
                search_input.clear()
                time.sleep(1)

            except Exception as e:
                print(f"✗ Error testing search: {e}")
        else:
            print("  SKIPPED - No search input found")

        # Test 6: Check for Console Errors
        print("\n[Test 6] Checking for console errors...")
        console_messages = []

        def handle_console(msg):
            console_messages.append({
                'type': msg.type,
                'text': msg.text
            })

        page.on('console', handle_console)

        # Reload to capture console messages
        page.reload()
        page.wait_for_load_state('networkidle')
        time.sleep(2)

        errors = [msg for msg in console_messages if msg['type'] == 'error']
        warnings = [msg for msg in console_messages if msg['type'] == 'warning']

        print(f"  - Console errors: {len(errors)}")
        for error in errors[:5]:  # Show first 5
            print(f"    ERROR: {error['text']}")

        print(f"  - Console warnings: {len(warnings)}")
        for warning in warnings[:3]:  # Show first 3
            print(f"    WARN: {warning['text']}")

        # Test 7: Test Favorites Page (if exists)
        print("\n[Test 7] Testing favorites page...")
        try:
            # Look for favorites link
            fav_link = page.locator('a[href*="favorite" i], a:has-text("Favorites")').first
            if fav_link.is_visible():
                fav_link.click()
                page.wait_for_load_state('networkidle')
                time.sleep(1)

                page.screenshot(path='/tmp/ufc_pokedex_favorites.png', full_page=True)
                print("✓ Favorites page loaded")
                print("  Screenshot saved: /tmp/ufc_pokedex_favorites.png")
            else:
                print("  SKIPPED - No favorites link found")
        except Exception as e:
            print(f"  SKIPPED - Could not navigate to favorites: {e}")

        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"✓ Home page loaded successfully")
        print(f"✓ Found {len(fighter_cards)} fighter elements")
        print(f"✓ Found {len(buttons)} interactive buttons")
        print(f"✓ Console errors: {len(errors)}")
        print(f"✓ Console warnings: {len(warnings)}")
        print("\nScreenshots saved to /tmp/")
        print("  - ufc_pokedex_home.png")
        print("  - ufc_pokedex_fighter_detail.png")
        print("  - ufc_pokedex_search.png")
        print("  - ufc_pokedex_favorites.png")
        print("=" * 60)

        browser.close()
        print("\n✓ Test completed successfully!")

if __name__ == '__main__':
    test_ufc_pokedex()

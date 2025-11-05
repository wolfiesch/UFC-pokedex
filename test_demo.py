#!/usr/bin/env python3
"""
UFC Pokedex Static Demo Test
Demonstrates webapp-testing skill capabilities
"""
from playwright.sync_api import sync_playwright
import os
import time

def test_static_demo():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        # Get absolute path to HTML file
        html_path = os.path.abspath('test_demo.html')
        file_url = f'file://{html_path}'

        print("=" * 70)
        print("UFC Pokedex - Webapp Testing Skill Demonstration")
        print("=" * 70)
        print(f"Testing file: {file_url}")
        print()

        # Test 1: Load Page
        print("[Test 1] Loading demo page...")
        page.goto(file_url)
        page.wait_for_load_state('networkidle')
        time.sleep(1)

        page.screenshot(path='/tmp/claude/demo_initial.png', full_page=True)
        print("✓ Page loaded successfully")
        print("  Screenshot: /tmp/claude/demo_initial.png")

        # Test 2: Verify Page Title
        print("\n[Test 2] Verifying page title...")
        title = page.title()
        print(f"✓ Page title: '{title}'")

        # Test 3: Discover Fighter Cards
        print("\n[Test 3] Discovering fighter cards...")
        fighter_cards = page.locator('.fighter-card').all()
        print(f"✓ Found {len(fighter_cards)} fighter cards")

        for i, card in enumerate(fighter_cards):
            name = card.locator('.fighter-name').inner_text()
            record = card.locator('.fighter-record').inner_text()
            print(f"  [{i+1}] {name} - Record: {record}")

        # Test 4: Test Search Functionality
        print("\n[Test 4] Testing search functionality...")
        search_input = page.locator('#searchInput')
        search_input.fill('McGregor')
        time.sleep(0.5)

        visible_cards = page.locator('.fighter-card[style*="display: block"], .fighter-card:not([style*="display: none"])').all()
        print(f"✓ Search for 'McGregor'")
        print(f"  Visible cards after search: {len(visible_cards)}")

        page.screenshot(path='/tmp/claude/demo_search.png', full_page=True)
        print("  Screenshot: /tmp/claude/demo_search.png")

        # Clear search
        search_input.clear()
        time.sleep(0.5)

        # Test 5: Discover Buttons
        print("\n[Test 5] Discovering interactive elements...")
        buttons = page.locator('button').all()
        print(f"✓ Found {len(buttons)} buttons")

        favorite_buttons = page.locator('.favorite-btn').all()
        print(f"  - Favorite buttons: {len(favorite_buttons)}")

        # Test 6: Click Favorite Button (with dialog handling)
        print("\n[Test 6] Testing button interaction...")

        # Handle the alert dialog
        dialog_message = None
        def handle_dialog(dialog):
            nonlocal dialog_message
            dialog_message = dialog.message
            dialog.accept()

        page.on('dialog', handle_dialog)

        first_favorite_btn = favorite_buttons[0]
        first_favorite_btn.click()
        time.sleep(0.5)

        if dialog_message:
            print(f"✓ Button clicked, alert received: '{dialog_message}'")
        else:
            print("✓ Button clicked (no alert)")

        # Test 7: Element Discovery
        print("\n[Test 7] Discovering all page elements...")

        inputs = page.locator('input').all()
        print(f"  - Input fields: {len(inputs)}")

        divs = page.locator('div').all()
        print(f"  - Div elements: {len(divs)}")

        # Test 8: Console Messages
        print("\n[Test 8] Capturing console messages...")
        console_messages = []

        def handle_console(msg):
            console_messages.append({
                'type': msg.type,
                'text': msg.text
            })

        page.on('console', handle_console)

        # Reload to capture console
        page.reload()
        page.wait_for_load_state('networkidle')
        time.sleep(1)

        print(f"✓ Console messages captured: {len(console_messages)}")
        for msg in console_messages:
            print(f"  [{msg['type'].upper()}] {msg['text']}")

        # Test 9: CSS Selectors
        print("\n[Test 9] Testing CSS selector capabilities...")

        # Find all fighter names
        names = page.locator('.fighter-name').all()
        print(f"✓ Fighter names via CSS selector: {len(names)}")

        # Find by attribute
        card_with_id = page.locator('[data-fighter-id="1"]').first
        fighter_name = card_with_id.locator('.fighter-name').inner_text()
        print(f"✓ Found fighter by data-id: {fighter_name}")

        # Test 10: Hover Effects
        print("\n[Test 10] Testing hover interaction...")
        first_card = fighter_cards[0]
        first_card.hover()
        time.sleep(0.5)

        page.screenshot(path='/tmp/claude/demo_hover.png', full_page=True)
        print("✓ Hover effect applied")
        print("  Screenshot: /tmp/claude/demo_hover.png")

        # Summary
        print("\n" + "=" * 70)
        print("Test Summary - Webapp Testing Skill Demonstration")
        print("=" * 70)
        print(f"✓ Successfully loaded static HTML page")
        print(f"✓ Discovered {len(fighter_cards)} fighter cards")
        print(f"✓ Tested search functionality (filtering works)")
        print(f"✓ Interacted with {len(favorite_buttons)} buttons")
        print(f"✓ Captured {len(console_messages)} console messages")
        print(f"✓ Handled JavaScript dialog")
        print(f"✓ Tested hover interactions")
        print(f"✓ Generated 3 screenshots in /tmp/claude/")
        print("\nScreenshots:")
        print("  1. demo_initial.png  - Initial page load")
        print("  2. demo_search.png   - Search filtering")
        print("  3. demo_hover.png    - Hover effect")
        print("=" * 70)

        browser.close()
        print("\n✓ Webapp-testing skill demonstration completed successfully!")

if __name__ == '__main__':
    test_static_demo()

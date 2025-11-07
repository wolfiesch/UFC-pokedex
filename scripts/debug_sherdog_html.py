#!/usr/bin/env python3
"""Debug script to fetch and analyze Sherdog fighter page HTML structure."""

import json
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def fetch_sherdog_page(sherdog_url: str) -> str:
    """Fetch a Sherdog fighter page.

    Args:
        sherdog_url: URL to Sherdog fighter profile

    Returns:
        HTML content as string
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    response = requests.get(sherdog_url, headers=headers, timeout=10)
    response.raise_for_status()

    return response.text


def analyze_html_structure(html: str, fighter_name: str):
    """Analyze and print HTML structure to find bio data.

    Args:
        html: HTML content
        fighter_name: Name of fighter for logging
    """
    soup = BeautifulSoup(html, "html.parser")

    print(f"\n{'='*80}")
    print(f"Analyzing HTML for: {fighter_name}")
    print(f"{'='*80}\n")

    # Look for common bio/vitals sections
    print("🔍 Searching for bio sections...\n")

    bio_candidates = [
        ("div.module.bio_fighter", soup.select("div.module.bio_fighter")),
        ("div.bio", soup.select("div.bio")),
        ("div.content.table", soup.select("div.content.table")),
        ("div.bio_graph", soup.select("div.bio_graph")),
        ("section.module.fighter_stats", soup.select("section.module.fighter_stats")),
    ]

    for selector, elements in bio_candidates:
        if elements:
            print(f"✓ Found {len(elements)} element(s) with selector: {selector}")
            for idx, elem in enumerate(elements[:2], 1):  # Show first 2
                print(f"\n  Element {idx} preview:")
                print(f"  {str(elem)[:500]}")
        else:
            print(f"✗ No elements found for: {selector}")

    print(f"\n{'='*80}")
    print("🔍 Looking for specific data fields...\n")

    # Look for specific fields
    fields_to_check = [
        ("Birthday/Born", ["strong:contains('Birthday')", "strong:contains('Born')",
                          "span.birthday", "span.item.birthday"]),
        ("Height", ["strong:contains('Height')", "span.height", "span.item.height"]),
        ("Weight", ["strong:contains('Weight')", "span.weight", "span.item.weight"]),
        ("Reach", ["strong:contains('Reach')", "span.reach", "span.item"]),
    ]

    for field_name, selectors in fields_to_check:
        print(f"{field_name}:")
        found_any = False
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                found_any = True
                print(f"  ✓ {selector}: {len(elements)} found")
                for elem in elements[:2]:
                    print(f"    → {elem}")
        if not found_any:
            print(f"  ✗ None found")
        print()

    # Save full HTML for manual inspection
    debug_file = Path("data") / "debug_sherdog.html"
    debug_file.parent.mkdir(exist_ok=True)
    debug_file.write_text(html)
    print(f"💾 Full HTML saved to: {debug_file}")


def main():
    """Main entry point."""
    # Load a high-confidence match from sherdog_matches.json
    matches_file = Path("data/processed/sherdog_matches.json")

    if not matches_file.exists():
        print(f"❌ Error: {matches_file} not found")
        print("Run: make scrape-sherdog-search first")
        sys.exit(1)

    with matches_file.open() as f:
        matches = json.load(f)

    # Find first fighter with high confidence
    for ufc_id, data in matches.items():
        if data["matches"] and data["matches"][0]["confidence"] >= 70:
            fighter_name = data["ufc_fighter"]["name"]
            sherdog_url = data["matches"][0]["sherdog_url"]
            confidence = data["matches"][0]["confidence"]

            print(f"📊 Selected fighter: {fighter_name}")
            print(f"🔗 Sherdog URL: {sherdog_url}")
            print(f"✅ Match confidence: {confidence}%")

            try:
                html = fetch_sherdog_page(sherdog_url)
                analyze_html_structure(html, fighter_name)
                print(f"\n{'='*80}")
                print("✅ Analysis complete!")
                print(f"{'='*80}\n")
                break
            except (requests.exceptions.RequestException, OSError) as e:
                print(f"❌ Error fetching page: {e}")
                print("Trying next fighter...")
                continue
    else:
        print("❌ No high-confidence matches found")
        sys.exit(1)


if __name__ == "__main__":
    main()

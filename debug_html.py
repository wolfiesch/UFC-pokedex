#!/usr/bin/env python3
"""Debug script to fetch and examine HTML structure from UFCStats.com"""

import requests
from parsel import Selector

# Fetch Jon Jones' fighter page
url = "http://ufcstats.com/fighter-details/07f72a2a7591b409"
headers = {
    "User-Agent": "UFC-Pokedex-Scraper/0.1 (+local)"
}

print(f"Fetching {url}...")
response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    selector = Selector(text=response.text)

    # Find the fight history table
    table = selector.css("table.b-fight-details__table")
    if table:
        print("Found fight history table!")

        # Check table headers
        print("\nTable Headers:")
        headers = table.css("thead th")
        for idx, header in enumerate(headers, 1):
            header_text = " ".join([t.strip() for t in header.css("::text").getall() if t.strip()])
            print(f"  Column {idx}: {header_text}")

        rows = table.css("tbody tr") or table.css("tr.b-fight-details__table-row")
        print(f"\nNumber of fight rows: {len(rows)}\n")

        if rows:
            # Examine the first real fight (not the header row)
            for idx, row in enumerate(rows[:3]):
                print(f"=== Row {idx + 1} ===")

                # Get the HTML of specific stat cells
                sig_strikes_cell = row.css("td:nth-child(3)")
                sig_strikes_pct_cell = row.css("td:nth-child(4)")
                total_strikes_cell = row.css("td:nth-child(5)")
                takedowns_cell = row.css("td:nth-child(6)")

                if sig_strikes_cell:
                    print("\nSig Strikes cell (td:nth-child(3)):")
                    print("  HTML:", sig_strikes_cell.get()[:200])
                    print("  All text:", sig_strikes_cell.css("::text").getall())
                    print("  Extracted:", " ".join([t.strip() for t in sig_strikes_cell.css("::text").getall() if t.strip()]))

                if sig_strikes_pct_cell:
                    print("\nSig Strikes % cell (td:nth-child(4)):")
                    print("  HTML:", sig_strikes_pct_cell.get()[:200])
                    print("  All text:", sig_strikes_pct_cell.css("::text").getall())
                    print("  Extracted:", " ".join([t.strip() for t in sig_strikes_pct_cell.css("::text").getall() if t.strip()]))

                print("\n" + "="*50 + "\n")

    # Look for any tables
    print("\n" + "="*70)
    all_tables = selector.css("table")
    print(f"\nTotal tables found: {len(all_tables)}")

    for idx, tbl in enumerate(all_tables):
        classes = tbl.css("::attr(class)").get()
        print(f"  Table {idx + 1}: class='{classes}'")

        # Show headers for each table
        headers = tbl.css("thead th, th")
        if headers:
            header_texts = [" ".join([t.strip() for t in h.css("::text").getall() if t.strip()]) for h in headers]
            print(f"    Headers: {header_texts}")
else:
    print(f"Failed to fetch page: {response.status_code}")

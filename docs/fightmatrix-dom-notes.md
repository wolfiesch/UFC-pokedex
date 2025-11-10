# Fight Matrix DOM Structure - Reconnaissance Notes

**Date:** 2025-11-09
**Purpose:** Phase 3 - Historical Rankings Scraper Implementation
**Analyst:** Claude Code

---

## Overview

Fight Matrix provides historical MMA rankings through a web interface that uses **monthly snapshots** dating back to 2008. Historical data is **scrapable** via HTML tables with proper navigation.

---

## Key URLs

### Current Rankings
- Base: `https://www.fightmatrix.com/mma-ranks/`
- Division pages: `https://www.fightmatrix.com/mma-ranks/{division-slug}/`
  - Example: `https://www.fightmatrix.com/mma-ranks/lightweight/`

### Historical Rankings (Snapshots)
- Base: `https://www.fightmatrix.com/historical-mma-rankings/ranking-snapshots/`
- Parameterized: `?Issue={issue_number}&Division={division_code}`
  - Example: `?Issue=996&Division=7` (Issue #996, Bantamweight)
  - **Pagination:** `&Page={page_number}` for fighters beyond rank 25

### URL Pattern Discovery
- Issue numbers appear to increment sequentially
- Division codes are numeric (1-18+ range)
- Historical data requires **both Issue and Division** parameters
- Missing or invalid Issue parameters result in empty tables

---

## Data Availability

### Historical Coverage
- **Start Date:** January 20, 2008 (earliest available)
- **End Date:** November 2, 2025 (most recent at time of analysis)
- **Update Frequency:** Monthly (typically first week of each month)
- **Total History:** ~17 years of data

### Monthly Snapshots (Last 12 Months)
```
11/02/2025, 10/05/2025, 09/07/2025, 08/03/2025, 07/06/2025, 06/01/2025
05/04/2025, 04/06/2025, 03/02/2025, 02/02/2025, 01/05/2025, 12/01/2024
```

### Data Format
- **Type:** HTML tables (NOT PDFs for recent data)
- **Dynamic Loading:** Dropdown selection triggers page navigation
- **JavaScript:** Page uses jQuery for interactivity
- **Pagination:** 25 fighters per page, 50-60 pages per division

---

## Division Codes & Names

### Men's Divisions (Fight Matrix Labels)
| Code | Division Name        | UFC Equivalent           |
|------|----------------------|--------------------------|
| ?    | Pound-for-Pound      | N/A (aggregate ranking)  |
| ?    | Division Dominance   | N/A (metric ranking)     |
| ?    | Heavyweight          | Heavyweight              |
| ?    | LightHeavyweight     | Light Heavyweight        |
| ?    | Middleweight         | Middleweight             |
| ?    | Welterweight         | Welterweight             |
| ?    | Lightweight          | Lightweight              |
| ?    | Featherweight        | Featherweight            |
| 7    | Bantamweight         | Bantamweight (confirmed) |
| ?    | Flyweight            | Flyweight                |
| ?    | Strawweight          | Strawweight              |

### Women's Divisions
| Code | Division Name                | UFC Equivalent           |
|------|------------------------------|--------------------------|
| ?    | Women Pound-for-Pound        | N/A                      |
| ?    | Women - Division Dominance   | N/A                      |
| ?    | Women - Featherweight+       | Women's Featherweight    |
| ?    | Women - Bantamweight         | Women's Bantamweight     |
| ?    | Women - Flyweight            | Women's Flyweight        |
| ?    | Women - Strawweight          | Women's Strawweight      |
| ?    | Women - Atomweight           | Women's Atomweight       |

**Note:** Only Division 7 (Bantamweight) was confirmed during testing. Other codes need reverse-engineering.

---

## HTML Structure (Historical Snapshots)

### Page Layout
```html
<article>
  <h1>Published Ranking Snapshots</h1>

  <!-- Navigation Controls -->
  <div>
    <strong>Ranked Fighters:</strong> 1-25
    <a href="?Issue=996&Division=7&Page=2">></a>
    <a href="?Issue=996&Division=7&Page=55">>></a>
  </div>

  <a href="?Issue=992&Division=7"><< Previous Issue</a>

  <!-- Issue & Division Selectors -->
  <table>
    <tr>
      <td>
        <strong>Issue</strong>
        <select name="Issue">
          <option value="11/02/2025" selected>11/02/2025</option>
          <!-- More options... -->
        </select>
      </td>
      <td>
        <strong>Division</strong>
        <select name="Division">
          <option value="7" selected>Bantamweight</option>
          <!-- More options... -->
        </select>
      </td>
    </tr>
  </table>

  <!-- Rankings Table -->
  <table>
    <thead>
      <tr>
        <th>Rank</th>
        <th>↑ ↓</th>
        <th>Fighter</th>
        <th>Points</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>1</td>
        <td></td> <!-- Empty if no movement -->
        <td>
          <img src="flag.png" />
          <a href="/fighter-profile/Merab%20Dvalishvili/126964/">
            <strong>Merab Dvalishvili</strong>
          </a>
        </td>
        <td><div>2389</div></td>
      </tr>
      <tr>
        <td>3</td>
        <td>1</td> <!-- Moved up 1 position -->
        <td>
          <img src="flag.png" />
          <a href="/fighter-profile/Umar%20Nurmagomedov/168206/">
            <strong>Umar Nurmagomedov</strong>
          </a>
        </td>
        <td><div>1099</div></td>
      </tr>
      <tr>
        <td>4</td>
        <td>-1</td> <!-- Moved down 1 position -->
        <td>
          <img src="flag.png" />
          <a href="/fighter-profile/Petr%20Yan/141553/">
            <strong>Petr Yan</strong>
          </a>
        </td>
        <td><div>960</div></td>
      </tr>
      <!-- More rows... -->
    </tbody>
  </table>
</article>
```

---

## CSS Selectors for Scraping

### Rankings Table
```python
# Table selection
rankings_table = response.css('table')[1]  # Second table on page

# Headers (verify structure)
headers = rankings_table.css('thead tr th::text').getall()
# Expected: ["Rank", "↑ ↓", "Fighter", "Points"]

# Fighter rows
fighter_rows = rankings_table.css('tbody tr')
```

### Per-Row Extraction
```python
for row in fighter_rows:
    # Rank number
    rank = row.css('td:nth-child(1)::text').get().strip()

    # Movement indicator (may be empty)
    movement = row.css('td:nth-child(2)::text').get()
    if movement:
        movement = movement.strip()

    # Fighter name and profile URL
    fighter_name = row.css('td:nth-child(3) a strong::text').get()
    fighter_url = row.css('td:nth-child(3) a::attr(href)').get()

    # Points/rating
    points = row.css('td:nth-child(4) div::text').get().strip()
```

### Issue & Division Dropdowns
```python
# Get all available issues
issues = response.css('select[name="Issue"] option::text').getall()
# Returns: ['- Select Issue -', '11/02/2025', '10/05/2025', ...]

# Get all divisions
divisions = response.css('select[name="Division"] option::text').getall()
# Returns: ['- Select Division -', 'Pound-for-Pound', 'Bantamweight', ...]
```

### Pagination Links
```python
# Check if more pages exist
next_page = response.css('a:contains(">")::attr(href)').get()
# Example: "/historical-mma-rankings/ranking-snapshots/?Issue=996&Division=7&Page=2"

last_page = response.css('a:contains(">>")::attr(href)').get()
# Example: "/historical-mma-rankings/ranking-snapshots/?Issue=996&Division=7&Page=55"
```

---

## Date Stamping

### Issue Date Format
- **Display Format:** `MM/DD/YYYY` (e.g., "11/02/2025")
- **Storage:** Available in dropdown `option` values
- **Parsing Strategy:** Use dropdown value as canonical date

### Issue Number Mapping
- Issue numbers are sequential integers (e.g., 996, 992, 988)
- **Decrement pattern:** ~4 issues per month (weekly cadence likely)
- **NOT directly correlated to date** - use dropdown dates instead

### Extracting Date from Page
```python
# From selected dropdown option
selected_issue = response.css('select[name="Issue"] option[selected]::text').get()
# Returns: "11/02/2025"

# Convert to Python date
from datetime import datetime
rank_date = datetime.strptime(selected_issue, "%m/%d/%Y").date()
```

---

## Pagination Strategy

### Fighters Per Division
- Fight Matrix ranks **750+ fighters per division** (stated on site)
- Historical snapshots show **25 fighters per page**
- **Total pages:** 50-60 pages per division (e.g., Bantamweight had 55 pages)

### Scraping Approach
**SELECTED: Scrape Top 50 Fighters (2 pages per division)**
   - **Rationale:** Better peak ranking detection without data explosion
   - **Coverage:** Ranks 1-50 per division (2 pages × 25 fighters/page)
   - **Request Load:** 11 divisions × 12 months × 2 pages = ~264 requests
   - **Total Time:** ~13 minutes with 3-second delays
   - **Benefits:**
     - Captures rising contenders outside top 25
     - More comprehensive historical trends for peak calculations
     - Still avoids massive dataset (vs. 7,260 requests for all fighters)

**Alternative Options (not selected):**
1. **Top 25 Only** - Single page, faster but misses deeper history
2. **All Ranked Fighters** - 55 pages × 11 divisions × 12 months = ~7,260 requests (too heavy)

---

## JavaScript Dependencies

### Dynamic Behavior
- **Dropdown Selection:** Triggers full page navigation (not AJAX)
- **Table Loading:** Data loads on initial page render (no lazy loading)
- **Fighter Links:** Standard `<a>` tags with profile URLs

### Scraping Implications
- **No JavaScript execution required** for basic scraping
- Playwright/Selenium optional (can use Scrapy alone)
- Dropdown navigation handled via direct URL parameters

---

## Rate Limiting & Robots.txt

### Observed Behavior
- No immediate IP blocking during testing
- Standard WordPress site with jQuery
- No aggressive anti-scraping measures detected

### Recommended Settings
```python
# settings.py (Scrapy)
DOWNLOAD_DELAY = 3  # 3 seconds between requests
CONCURRENT_REQUESTS = 2  # Conservative parallelism
ROBOTSTXT_OBEY = True  # Respect robots.txt

USER_AGENT = 'UFC-Pokedex-Scraper/0.1 (+https://github.com/your-repo)'
```

### Robots.txt Check
**TODO:** Verify `https://www.fightmatrix.com/robots.txt` before implementation

---

## Critical Findings & Blockers

### ✅ WORKING
1. **Historical data is scrapable** - HTML tables with full data
2. **17 years of history** available (2008-2025)
3. **Monthly cadence** for snapshots (12-13 per year)
4. **Pagination** is straightforward (query parameter)
5. **Fighter names** are clean (no encoding issues observed)

### ⚠️ CHALLENGES
1. **Division codes unknown** - Only confirmed Division 7 = Bantamweight
2. **Issue number pattern unclear** - Need to reverse-engineer Issue → Date mapping
3. **No direct date in HTML** - Must rely on dropdown selection text
4. **Large dataset** - 11 divisions × 12 months × 25-55 pages = potential for thousands of requests
5. **No API** - Must scrape HTML (no structured data feed)

### 🚧 REQUIRED BEFORE IMPLEMENTATION
1. **Map all division codes** - Test each division dropdown option to determine numeric codes
2. **Determine Issue number range** - Find Issue numbers for last 12 months
3. **Validate robots.txt** - Ensure scraping is permitted
4. **Test rate limits** - Verify 3-second delay is acceptable
5. ~~**Decide on pagination scope**~~ - ✅ **DECIDED: Top 50 fighters (2 pages per division)**

---

## Scraper Implementation Plan

### Phase 3.1: Division Code Mapping (Next Step)
```python
# Spider: fightmatrix_division_mapper.py
# Purpose: Discover division codes by testing each dropdown option
# Output: Division name → Division code mapping (JSON)
```

### Phase 3.2: Issue Number Discovery
```python
# Spider: fightmatrix_issue_scanner.py
# Purpose: Find valid Issue numbers for target date range (12 months)
# Strategy: Binary search or sequential scan from known Issue 996
```

### Phase 3.3: Historical Rankings Spider
```python
# Spider: fightmatrix_rankings.py
# Purpose: Scrape rankings for all divisions × 12 monthly snapshots
# Arguments: --start-date, --end-date, --divisions, --top-n (default 50)
# Default: Top 50 fighters (2 pages per division)
```

---

## Example Data Sample

### Bantamweight Division (Issue #996, 11/02/2025)
```json
[
  {
    "rank": 1,
    "fighter_name": "Merab Dvalishvili",
    "fighter_url": "/fighter-profile/Merab%20Dvalishvili/126964/",
    "points": 2389,
    "movement": null,
    "division": "Bantamweight",
    "rank_date": "2025-11-02",
    "source": "fightmatrix",
    "issue_number": 996
  },
  {
    "rank": 3,
    "fighter_name": "Umar Nurmagomedov",
    "fighter_url": "/fighter-profile/Umar%20Nurmagomedov/168206/",
    "points": 1099,
    "movement": 1,
    "division": "Bantamweight",
    "rank_date": "2025-11-02",
    "source": "fightmatrix",
    "issue_number": 996
  },
  {
    "rank": 4,
    "fighter_name": "Petr Yan",
    "fighter_url": "/fighter-profile/Petr%20Yan/141553/",
    "points": 960,
    "movement": -1,
    "division": "Bantamweight",
    "rank_date": "2025-11-02",
    "source": "fightmatrix",
    "issue_number": 996
  }
]
```

---

## Division Normalization Requirements

Fight Matrix uses different naming conventions than UFC:
- "LightHeavyweight" → "Light Heavyweight"
- "Pound-for-Pound" → Skip (not a weight class)
- "Division Dominance" → Skip (aggregate metric)
- "Women - Featherweight+" → "Women's Featherweight"

**Normalization function needed** (similar to UFC parser):
```python
def normalize_fightmatrix_division(division_name: str) -> str:
    """
    Normalize Fight Matrix division names to internal schema.
    """
    mapping = {
        "LightHeavyweight": "Light Heavyweight",
        "Women - Featherweight+": "Women's Featherweight",
        "Women - Bantamweight": "Women's Bantamweight",
        # ... more mappings
    }
    return mapping.get(division_name, division_name)
```

---

## Next Steps

### Immediate (Phase 3 Milestone 1 Completion)
- [x] Verify Fight Matrix has historical data
- [x] Confirm data is scrapable (not PDFs)
- [x] Document HTML structure
- [x] Identify CSS selectors
- [x] Create reconnaissance notes document

### Upcoming (Phase 3 Milestone 2)
- [ ] Create division code mapper spider
- [ ] Test all 18 division dropdown options
- [ ] Generate division name → code mapping
- [ ] Determine Issue number range for last 12 months
- [ ] Validate robots.txt compliance

---

## References

- Fight Matrix Historical Snapshots: https://www.fightmatrix.com/historical-mma-rankings/ranking-snapshots/
- Fight Matrix Current Rankings: https://www.fightmatrix.com/mma-ranks/
- Screenshot: `.playwright-mcp/fightmatrix_historical.png`

**End of Reconnaissance Notes**

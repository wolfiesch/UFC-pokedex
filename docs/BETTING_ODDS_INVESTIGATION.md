# Betting Odds Scraping - Technical Investigation

## Summary

We successfully built scrapers for Best Fight Odds but encountered a **technical limitation** with extracting the actual betting odds values. This document details the investigation and proposes solutions.

## What Works ✅

1. **Archive Scraper** (`bestfightodds_archive`)
   - ✅ Scrapes event list from archive page
   - ✅ Extracts event names, dates, URLs, organizations
   - ✅ Tested successfully: 20 events scraped

2. **Event Detail Scraper** (`bestfightodds_event`)
   - ✅ Scrapes fight matchups from individual events
   - ✅ Extracts fighter names, matchup IDs, profile URLs
   - ✅ Tested successfully: 13 matchups scraped from UFC Vegas 110

3. **Playwright Integration** (`bestfightodds_event_playwright`)
   - ✅ Successfully installed Scrapy-Playwright
   - ✅ Browser automation working correctly
   - ✅ JavaScript rendering confirmed
   - ❌ Odds data still not extractable

## The Problem ❌

### Odds Data is Not in HTML

**Initial HTML (No Odds):**
```html
<tr id="mu-40336">
  <th scope="row">
    <a href="/fighters/David-Onama-10808">David Onama</a>
  </th>
</tr>
```

**Expected (With Odds - Not Found):**
```html
<td data-bookie="draftkings">-150</td>
<td data-bookie="fanduel">-145</td>
```

### Investigation Findings

1. **Static HTML**: The initial page load contains ZERO odds values
2. **JavaScript Loading**: Odds loaded by `/js/bfo.min.js` (minified, 32 lines)
3. **No API Calls Visible**: No obvious AJAX/fetch endpoints in source
4. **Data Attributes Missing**: No `data-bookie` attributes in rendered HTML
5. **Playwright Didn't Help**: Even with full JavaScript rendering, odds cells are empty

### Possible Explanations

1. **Delayed Loading**: Odds might load after our 2-second wait
2. **User Interaction Required**: Might need to click/hover to reveal odds
3. **Paywall/Login**: Free tier might not show historical odds
4. **API Authentication**: Odds endpoint might require tokens/cookies
5. **WebSocket/Real-time**: Odds pushed via WebSocket after page load

## Tested Approaches ❌

### Approach 1: Basic Scraping
- ❌ No odds in static HTML

### Approach 2: Playwright JavaScript Rendering
- ❌ Odds still empty after JavaScript execution
- ✅ Page renders correctly, just without odds values

### Approach 3: JavaScript Variable Inspection
- ❌ No global JavaScript variables found with odds data
- Checked for: `window.*odds*`, `var/let/const`, embedded JSON

## Alternative Solutions ✅

Since direct scraping has hit a wall, here are viable alternatives:

### Option 1: Use Pre-Existing Datasets (RECOMMENDED)

**GitHub: jansen88/ufc-data**
- Coverage: Nov 2014 - 2023
- Format: CSV with favorite/underdog odds
- Source: betmma.tips
- Status: Ready to use

**Kaggle: UFC Fights 2010-2020**
- Coverage: 2010-2020
- Format: CSV dataset
- Status: Download and import

**Advantages:**
- ✅ Immediate access to historical data
- ✅ Clean, structured format
- ✅ No scraping required
- ✅ Covers most recent history

### Option 2: The Odds API (Paid Service)

**Service:** https://the-odds-api.com
- Coverage: Mid-2020 to present
- Format: JSON API
- Cost: Free tier available, paid for historical
- Bookmakers: 12+ including DraftKings

**Advantages:**
- ✅ Legal, ToS-compliant
- ✅ Real-time and historical data
- ✅ JSON format (easy to integrate)
- ✅ Well-documented

**Implementation:**
```python
import requests

API_KEY = "your_key_here"
url = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/odds"
response = requests.get(url, params={"apiKey": API_KEY, "regions": "us"})
odds_data = response.json()
```

### Option 3: Manual Browser Automation (Last Resort)

If you absolutely need Best Fight Odds data:

1. **Use Selenium with human-like delays**
   ```python
   from selenium import webdriver
   import time

   driver = webdriver.Chrome()
   driver.get("https://www.bestfightodds.com/events/ufc-vegas-110-3913")
   time.sleep(10)  # Wait for odds to load

   # Try to interact with page
   driver.execute_script("window.scrollTo(0, 500)")
   time.sleep(5)

   # Extract after user interaction
   odds_elements = driver.find_elements_by_css_selector("[data-bookie]")
   ```

2. **Browser DevTools Investigation**
   - Open event page in Chrome
   - Open DevTools > Network tab
   - Clear and reload page
   - Look for XHR/Fetch requests with odds data
   - Find the API endpoint and reverse-engineer it

3. **Contact Best Fight Odds**
   - Some sites offer API access for researchers
   - Explain your use case (educational/research)
   - They might provide access or guidance

## Recommended Workflow

### Phase 1: Use Existing Data (Immediate)
```bash
# Download from GitHub
git clone https://github.com/jansen88/ufc-match-predictor
cp ufc-match-predictor/data/complete_ufc_data.csv data/betting_odds/

# Or download from Kaggle
kaggle datasets download -d mdabbert/ufc-fights-2010-2020-with-betting-odds
unzip ufc-fights-2010-2020-with-betting-odds.zip -d data/betting_odds/
```

### Phase 2: Supplement with The Odds API (Recent Data)
```bash
# Install requests
uv pip install requests

# Create script to fetch recent odds
python scripts/fetch_recent_odds_from_api.py
```

### Phase 3: Integrate into Database
```python
# Load historical odds from CSV
import pandas as pd

odds_df = pd.read_csv("data/betting_odds/complete_ufc_data.csv")

# Filter for betting odds columns
betting_cols = ["favorite_odds", "underdog_odds", "betting_outcome"]
odds_data = odds_df[betting_cols]

# Insert into database
# (Add your database insertion logic here)
```

## Data Schema (From Existing Datasets)

### GitHub jansen88/ufc-data Format:
```csv
date,fighter_1,fighter_2,favorite_odds,underdog_odds,betting_outcome
2023-12-16,Leon Edwards,Colby Covington,-200,+170,Favorite Won
```

### The Odds API Format:
```json
{
  "id": "abc123",
  "sport_key": "mma_mixed_martial_arts",
  "commence_time": "2025-11-15T02:00:00Z",
  "home_team": "Fighter A",
  "away_team": "Fighter B",
  "bookmakers": [
    {
      "key": "draftkings",
      "title": "DraftKings",
      "markets": [
        {
          "key": "h2h",
          "outcomes": [
            {"name": "Fighter A", "price": -150},
            {"name": "Fighter B", "price": +130}
          ]
        }
      ]
    }
  ]
}
```

## Files Created

### Functional Scrapers:
1. `scraper/spiders/bestfightodds_archive.py` - ✅ Working
2. `scraper/spiders/bestfightodds_event.py` - ✅ Working (matchups only)
3. `scraper/spiders/bestfightodds_event_playwright.py` - ✅ Working (matchups only)

### Documentation:
1. `docs/BETTING_ODDS_SCRAPER.md` - Complete scraper guide
2. `docs/BETTING_ODDS_INVESTIGATION.md` - This document
3. `scraper/spiders/README_BETTING_ODDS.md` - Quick reference

## Next Steps

**Recommended Action Plan:**

1. ✅ **Use jansen88/ufc-data** for historical odds (2014-2023)
2. ✅ **Sign up for The Odds API** free tier for recent data (2020+)
3. ⏸️ **Pause Best Fight Odds scraping** until we can reverse-engineer their API
4. 📊 **Focus on data analysis** with existing odds data

**If you need Best Fight Odds specifically:**
1. Manual browser investigation with DevTools (Network tab)
2. Look for XHR/Fetch requests during page load
3. Try contacting them for research API access

---

**Status:** ✅ Matchup scraping functional | ❌ Odds scraping blocked | ✅ Alternatives documented

**Last Updated:** November 12, 2025

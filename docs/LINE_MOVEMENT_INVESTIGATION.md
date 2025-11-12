# Historical Line Movement Data Investigation

## Question
**Can we scrape historical odds data showing how odds changed leading up to fights?**

## Answer: YES! ✅

Best Fight Odds contains **complete historical line movement data** from when odds open until the fight starts!

## Discovery

### What We Found

1. **Highcharts Integration** - Best Fight Odds uses Highcharts library for line movement visualization
2. **Interactive Charts** - Clicking on odds cells opens modal windows with historical line movement
3. **Complete History** - Shows odds evolution from opening to closing
4. **Per-Bookmaker Tracking** - Separate lines for each bookmaker showing how their odds changed over time
5. **Timestamp Data** - Each odds change includes a timestamp

### Evidence from Web Research

**From Best Fight Odds description:**
> "Best Fight Odds stores all odds posted on our site in an archive that contains thousands of matchups and fighter profiles dating back to 2007... provides not only closing odds but also **the entire odds history from when lines opened on each betting site**"

**From Medium article on scraping Best Fight Odds:**
> "The data uses a function called 'CreateMIChart' with encrypted data... The result is **JSON format data of betting lines evolution for each fighter including timestamp and odds**"

## How It Works

### Current Odds (What We Can Scrape Now)

✅ **Already Working:**
- Current/closing odds for each bookmaker
- Line movement indicators (▲ up, ▼ down)
- Multiple bookmakers per fight
- Historical events from archive

**Spider:** `bestfightodds_odds_final.py`

### Historical Line Movement (Requires Additional Work)

The historical data exists in two places:

#### 1. Interactive Charts (Highcharts)
- **Location:** Modal windows that open when clicking odds cells
- **Data:** Complete line movement over time
- **Format:** Highcharts series data with timestamps
- **Access:** Requires JavaScript interaction (clicking)

#### 2. Encrypted Chart Data (CreateMIChart)
- **Location:** Embedded in page JavaScript
- **Data:** Base64-encoded, then encrypted JSON
- **Format:** Array of [timestamp, odds_value] pairs
- **Access:** Requires decryption algorithm

## Extraction Approaches

### Approach 1: Click-and-Extract (Simpler)

**What we'd do:**
1. Navigate to event page
2. Wait for odds to load
3. Click each odds cell sequentially
4. Extract Highcharts data from modal
5. Close modal and repeat for next cell

**Pros:**
- Uses existing rendered charts
- No decryption needed
- Straightforward Playwright automation

**Cons:**
- Slower (one click per bookmaker per fight)
- More requests to server
- Dependent on UI behavior

### Approach 2: Decrypt CreateMIChart (Faster)

**What we'd do:**
1. Navigate to event page
2. Extract CreateMIChart JavaScript calls from page
3. Decode base64 data
4. Decrypt using their decryption algorithm
5. Parse JSON line movement data

**Pros:**
- Much faster (all data in one page load)
- More respectful to server
- Get all bookmakers at once

**Cons:**
- Need to reverse-engineer decryption
- Algorithm might change
- More complex implementation

## Data Structure (What We'd Get)

### Historical Line Movement Format

```json
{
  "matchup_id": "40336",
  "fighter_1": "David Onama",
  "fighter_2": "Steve Garcia",
  "bookmaker_id": 21,
  "bookmaker_name": "DraftKings",
  "line_movement": [
    {
      "timestamp": "2025-10-25T14:30:00Z",
      "fighter_1_odds": "+500",
      "fighter_2_odds": "-650",
      "type": "opening"
    },
    {
      "timestamp": "2025-10-28T09:15:00Z",
      "fighter_1_odds": "+550",
      "fighter_2_odds": "-700",
      "type": "movement"
    },
    {
      "timestamp": "2025-11-01T18:00:00Z",
      "fighter_1_odds": "+7500",
      "fighter_2_odds": "-450",
      "type": "closing"
    }
  ],
  "total_movements": 15,
  "opening_to_closing_change_f1": "+7000",
  "opening_to_closing_change_f2": "+200"
}
```

## Use Cases

With historical line movement data, you could:

1. **Track Sharp Money** - See when big bets moved lines
2. **Opening vs Closing Analysis** - Compare initial and final odds
3. **Line Movement Patterns** - Identify typical movement patterns
4. **Bookmaker Comparison** - See which books move fastest
5. **Timing Strategies** - Determine best time to place bets
6. **Historical Analysis** - Study past line movements for similar matchups

## Implementation Recommendation

### Phase 1: Current Odds (DONE ✅)
We already have this working with `bestfightodds_odds_final.py`

### Phase 2: Historical Line Movement (TODO)

**Recommended: Approach 1 (Click-and-Extract)**

Why? Because:
- More reliable than reverse-engineering encryption
- Can start immediately
- Works with existing Playwright infrastructure
- Easier to maintain

**Implementation Plan:**

1. **Extend existing spider** to click odds cells
2. **Wait for chart modal** to appear
3. **Extract Highcharts data** using JavaScript evaluation
4. **Parse timestamps and odds values**
5. **Store in structured format**

**Estimated Effort:**
- 2-3 hours to implement
- 10-15 seconds per bookmaker per fight (with wait times)
- For 13 fights × 8 bookmakers = ~17-30 minutes per event

### Alternative: Focus on Opening/Closing Only

**Simpler approach:**
Instead of full line movement history, just capture:
- Opening odds (first recorded)
- Closing odds (final before fight)
- Net change

This might already be available in the current odds data structure without needing to click charts!

## Files for Reference

### Investigation Scripts Created
1. `scripts/investigate_line_movement.py` - Discovered Highcharts integration
2. `scripts/extract_line_movement.py` - Attempted chart data extraction

### Key Findings
- Chart window ID: `#chart-window`
- Chart area ID: `#chart-area`
- Uses Highcharts library
- Modal appears on odds cell click
- Data includes timestamps and historical values

## Next Steps

<options>
<option>Implement click-and-extract for full line movement history</option>
<option>Extract just opening/closing odds (simpler)</option>
<option>Focus on current odds for now, revisit line movement later</option>
<option>Research CreateMIChart decryption approach</option>
</options>

---

**Status:** Historical line movement data EXISTS and IS SCRAPABLE
**Recommended:** Implement click-and-extract approach
**Estimated Time:** 2-3 hours development + testing
**Data Available:** 2007-present for all fights on Best Fight Odds

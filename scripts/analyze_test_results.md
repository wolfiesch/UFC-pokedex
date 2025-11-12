# Line Movement Scraping Test Results

## Test 1: UFC 73 (2007) - Older Event
- **Time**: 1 minute
- **Records scraped**: 18
- **Issue**: Bar chart format (fighter comparisons, not line movement)
- **Conclusion**: Very old events may have different chart formats

## Test 2: UFC 309 (Recent) - 5 Clicks Only
- **Time**: ~15 seconds (5 clicks × 3s)
- **Odds cells found**: 285 cells per matchup
- **Chart type**: Line (correct!)
- **Data format**: ✅ Correct - Unix timestamps + odds values
- **Series name**: Bookmaker name (FanDuel, etc.)

## Actual Time Estimates

### Per Event Calculations:
- **UFC 309**: 285 cells found for FIRST matchup only
- UFC events typically have: 10-13 fights
- Total cells per event: 285 × 10 = **2,850 clicks** (much higher than initial estimate!)
- Time per click: ~3 seconds
- **Total per event: 2,850 × 3s = 8,550s = 142 minutes (2.4 hours!)**

### Revised Estimates:

| Scenario | Events | Time per Event | Total Time |
|----------|--------|----------------|------------|
| **1 event (test)** | 1 | 2.4 hours | 2.4 hours |
| **Recent (2020-2025)** | ~150 | 2.4 hours | **360 hours (15 days!)** |
| **Full scrape (537)** | 537 | 2.4 hours | **1,289 hours (54 days!)** |

### Optimization Options:

1. **Limit clicks per event** (e.g., max 50 clicks):
   - Scrape sample of bookmakers, not all
   - Focus on major bookmakers (FanDuel, DraftKings, etc.)
   - Reduces time to: 537 × 50 × 3s / 3600 = **22 hours**

2. **Filter by event importance**:
   - Major numbered events only (UFC 200, 250, 300, etc.): ~100 events
   - Time: 100 × 2.4 hours = **240 hours (10 days)**

3. **Sample recent major events** (recommended):
   - Last 50 major events (2020-2025, numbered only)
   - Time: 50 × 2.4 hours = **120 hours (5 days)**

## Recommendations:

1. **DO NOT run full scrape** - 54 days is impractical
2. **Use max_clicks limit** to sample data efficiently
3. **Focus on recent events** (2020-2025)
4. **Limit to major bookmakers** (top 5-10)

## Alternative Approach:

Since the original scraper extracts **closing odds**, we actually have the most important data point (final odds at fight time). Historical line movement is interesting but not essential for most analyses.

**Suggested hybrid**:
- **Closing odds**: All 537 events (~1.6 hours) ✅
- **Line movement**: 20-30 major recent events with click limit (~60 hours)

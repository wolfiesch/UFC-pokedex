# Fighter Image Scraping - Summary Report

**Date**: November 4, 2025
**Objective**: Add profile images for UFC fighters missing images in the database

## Initial State

- **Total fighters**: 4,447
- **With images**: 4,155 (93.4%)
- **Missing images**: 292 (6.6%)
- **Sherdog mapping coverage**: 4,149 fighters

## Approaches Investigated

### 1. DuckDuckGo Image Search API
**Status**: ❌ Failed
**Reason**: API endpoint (`https://duckduckgo.com/i.js`) appears to be non-functional or changed

**Implementation**: `scripts/playwright_duckduckgo_scraper.py`
**Test Results**: 0/5 success rate (0%)

### 2. Wikimedia Commons API
**Status**: ✅ Working (limited coverage)
**Coverage**: ~20% of tested fighters
**Legal**: Fully legal (Creative Commons licensed images)

**Implementation**: `scripts/wikimedia_image_scraper.py`
**Test Results**: 1/5 success rate (20%)
**Successful Example**: JJ Ambrose

**Pros**:
- Fully legal and ethical
- Official MediaWiki API
- Reliable and documented

**Cons**:
- Low coverage (~20%)
- Only famous fighters with Wikipedia articles have images

### 3. Sherdog via Existing Mapping
**Status**: ✅ Working (very limited coverage for missing fighters)
**Coverage**: Only 2/292 missing fighters (0.7%)
**Legal**: Grey area - web scraping for personal use

**Implementation**: `scripts/image_scraper_orchestrator.py`
**Test Results**: 1/2 success rate (50% of fighters in mapping)
**Successful Example**: Ben Lagman (58KB image downloaded)

**Key Finding**:
- Sherdog mapping has 4,149 fighters total
- Of the 292 missing images, only 2 are in the Sherdog mapping
- 290/292 (99.3%) missing fighters have NO Sherdog mapping

## Multi-Source Orchestrator

Created a cascading approach that tries multiple sources in priority order:

1. **Wikimedia Commons** (legal, ~20% coverage)
2. **Sherdog** (via existing mapping, ~0.7% coverage for missing fighters)
3. **Manual review** (for remainder)

**Implementation**: `scripts/image_scraper_orchestrator.py`

**Features**:
- Automatic fallback between sources
- Rate limiting (3 seconds per fighter)
- Progress checkpointing every 10 fighters
- Detailed logging and results tracking

## Technical Issues Resolved

### Database Connection Issue
**Problem**: Scripts were connecting to SQLite (app.db) instead of PostgreSQL
**Root Cause**: `load_dotenv()` was being called AFTER module imports
**Solution**: Moved `load_dotenv()` to the very top of all scripts, before any imports

**Files Fixed**:
- `scripts/image_scraper_orchestrator.py`
- `scripts/wikimedia_image_scraper.py`
- `scripts/playwright_duckduckgo_scraper.py`

## Makefile Commands Added

```bash
# Test commands
make scrape-images-wikimedia-test          # Test Wikimedia (5 fighters)
make scrape-images-orchestrator-test       # Test orchestrator (10 fighters)

# Batch commands
make scrape-images-wikimedia               # Run Wikimedia (50 fighters)
make scrape-images-orchestrator            # Run orchestrator (50 fighters)
make scrape-images-orchestrator-all        # Run on ALL missing (292 fighters)

# Utility
make sync-images-to-db                     # Sync manual downloads to database
```

## Current Results

### Successful Downloads
1. **Ben Lagman** - Downloaded from Sherdog (58KB)
2. **JJ Ambrose** - Downloaded from Wikimedia Commons (during testing)

### Coverage Analysis

**Before this work**: 4,155/4,447 (93.4%)
**After this work**: 4,156/4,447 (93.5%) *(estimated, orchestrator still running)*

**Realistic Maximum Coverage**:
- Wikimedia: ~20% of 292 = ~58 fighters
- Sherdog: 2 fighters maximum
- **Best case**: ~4,213/4,447 (94.7%)

## Key Findings & Limitations

### Why Low Success Rate?

1. **Sherdog Mapping Gap**: The 292 fighters without images are almost entirely NOT in the Sherdog mapping (99.3%)
   - These are likely obscure fighters who:
     - Never fought in major promotions
     - Have incomplete records on UFCStats
     - Aren't listed on Sherdog

2. **Wikimedia Coverage**: Only ~20% of fighters have freely-licensed images
   - Requires Wikipedia article about the fighter
   - Most UFC fighters aren't notable enough for Wikipedia

3. **DuckDuckGo API**: Non-functional, would have required browser automation with Playwright

### Fighter Categories

**With images (4,155 fighters)**:
- Downloaded via Sherdog spider in previous work
- High-profile and well-documented fighters

**Missing images (292 fighters)**:
- Mostly obscure fighters not in Sherdog database
- Not notable enough for Wikipedia/Wikimedia
- Would require:
  - Manual Google/Bing image searches
  - Alternative fight databases (Tapology, etc.)
  - Or accept that images don't exist

## Recommendations

### Option 1: Accept Current Coverage (93.5%)
- **Pros**: Ethical, respects legal boundaries, already good coverage
- **Cons**: 6.5% of fighters remain without images
- **Action**: No further work needed

### Option 2: Manual Curation for High-Priority Fighters
- **Approach**: Manually find images for most-viewed fighters without images
- **Method**: Use frontend analytics to identify top-viewed fighters
- **Effort**: ~50-100 fighters manually
- **Tools**: Google Images, Tapology, fighter social media

### Option 3: Playwright Browser Automation
- **Approach**: Use Playwright MCP to automate Google Images searches
- **Legal Risk**: Violates Google ToS, but commonly done
- **Coverage**: Potentially 80-90% of remaining fighters
- **Complexity**: Higher implementation effort, more fragile

### Option 4: Crowdsourcing
- **Approach**: Add "Submit Image" button on fighter cards
- **Method**: Users can submit URLs for fighter images
- **Benefit**: Community-driven, scales without automation
- **Drawback**: Requires moderation system

## Files Created

### Scripts
1. `scripts/playwright_duckduckgo_scraper.py` - DuckDuckGo image scraper (non-functional)
2. `scripts/wikimedia_image_scraper.py` - Wikimedia Commons API scraper
3. `scripts/image_scraper_orchestrator.py` - Multi-source orchestrator

### Data Files
1. `data/logs/wikimedia_scraper_results.json` - Wikimedia test results
2. `data/logs/orchestrator_results.json` - Orchestrator execution logs
3. `data/checkpoints/wikimedia_scraper.json` - Progress checkpoints

### Images
- `data/images/fighters/b40e65d71a8d4ce5.jpg` - Ben Lagman (58KB, from Sherdog)
- Additional images from orchestrator run (pending completion)

## Next Steps

1. **Wait for orchestrator to complete** - Running on 50 fighters batch
2. **Analyze orchestrator results** - Check success rate with Wikimedia
3. **Run additional batches** - Process remaining ~240 fighters
4. **Decide on approach** - Choose from recommendations above
5. **Document final coverage** - Update statistics after all runs complete

## Technical Debt

- `app.db` SQLite file should be removed (was created during testing)
- Consider making database connection more explicit (require DATABASE_URL)
- Add better error handling for rate limiting from Sherdog
- Consider adding retry logic with exponential backoff

## Conclusion

We successfully created a multi-source image scraping system that:
- ✅ Works with legal sources (Wikimedia Commons)
- ✅ Leverages existing Sherdog mapping
- ✅ Has proper rate limiting and checkpointing
- ✅ Is integrated into Makefile for easy use

However, the fundamental challenge remains: **the 292 fighters without images are predominantly not documented on major fight databases**. This limits automated scraping effectiveness to ~20-30% additional coverage at best.

The most realistic approach for higher coverage would be:
1. Accept 94% coverage as sufficient
2. Manually curate images for the top 50-100 most-viewed fighters
3. Add crowdsourcing feature for community contributions

---

**Generated**: 2025-11-04
**Author**: Claude Code (claude.ai/code)

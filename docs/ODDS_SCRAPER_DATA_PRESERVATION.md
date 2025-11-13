# Betting Odds Scraper - Data Preservation & Regression Detection

## Overview

The betting odds scraper appends to `data/raw/bfo_odds_batch.jsonl` by default. To preserve historical data and detect regressions, we've implemented a comprehensive backup and versioning strategy.

## The Problem

**Issue**: Running the scraper multiple times overwrites or appends to the same file, making it impossible to:
- Compare different scraping runs
- Detect regression bugs (e.g., reverting to opening odds instead of closing odds)
- Track data quality over time
- Rollback to known-good datasets

**Solution**: Timestamped backups with metadata and comparison tools.

## Data Preservation Strategy

### 1. Automatic Backups Before Each Scrape

**Best Practice**: Always backup before running a new scrape:

```bash
# Backup current data with timestamp
./scripts/backup_scraper_data.sh

# Then run your scrape
make scrape-odds-optimized
```

### 2. Backup Script Usage

The backup script (`scripts/backup_scraper_data.sh`) provides three operations:

#### Create Backup
```bash
./scripts/backup_scraper_data.sh
# or
./scripts/backup_scraper_data.sh backup
```

**Output**:
```
✅ Backup created:
   📁 Data: data/raw/backups/bfo_odds_20251112_145600.jsonl
   📋 Meta: data/raw/backups/bfo_odds_20251112_145600.meta.json
   📊 Stats: 560 fights, 560K
```

#### List All Backups
```bash
./scripts/backup_scraper_data.sh --list
```

**Output**:
```
📦 Available backups:

📅 20251112_145600 (closing_odds_fix_v1)
   Date: 2025-11-12T22:56:00Z
   Fights: 560
   Size: 560K

📅 20251112_133000 (pre_fix_opening_odds)
   Date: 2025-11-12T21:30:00Z
   Fights: 520
   Size: 520K
```

#### Compare Two Backups (Regression Detection)
```bash
./scripts/backup_scraper_data.sh --compare \
    data/raw/backups/bfo_odds_20251112_133000.jsonl \
    data/raw/backups/bfo_odds_20251112_145600.jsonl
```

**Output**:
```
🔍 Comparing backups for regression detection...

📊 Backup 1 sample:
{
  "f1": "Dricus Du Plessis",
  "f2": "Sean Strickland",
  "fanduel": {
    "bookmaker_id": 21,
    "fighter_1_odds": "+3400▼",
    "fighter_2_odds": "-200▼"
  }
}

📊 Backup 2 sample:
{
  "f1": "Dricus Du Plessis",
  "f2": "Sean Strickland",
  "fanduel": {
    "bookmaker_id": 21,
    "fighter_1_odds": "-108▲",
    "fighter_2_odds": "-108▼"
  }
}

📈 Statistics comparison:
   Backup 1: 520 fights
   Backup 2: 560 fights

🔍 Checking for suspicious odds (regression indicators):
   Backup 1 suspicious odds: 45
   Backup 2 suspicious odds: 0
   ✅ Backup 2 has FEWER suspicious odds (improvement!)
```

### 3. Backup Metadata

Each backup includes a metadata file with:

```json
{
  "timestamp": "20251112_145600",
  "date": "2025-11-12T22:56:00Z",
  "fight_count": 560,
  "file_size": "560K",
  "source_file": "data/raw/bfo_odds_batch.jsonl",
  "backup_file": "data/raw/backups/bfo_odds_20251112_145600.jsonl",
  "scraper_version": "closing_odds_fix_v1",
  "notes": "Scraper fixed to extract closing odds only (3-element data-li arrays)"
}
```

## Regression Detection

### Known Regression Indicators

**Suspicious Odds Patterns** (opening/historical odds leaked through):
- `+3400` or higher (extreme underdog)
- `-10000` or lower (extreme favorite)
- These indicate the scraper is extracting opening odds instead of closing odds

### How to Detect Regressions

#### Method 1: Automated Comparison
```bash
# Compare your new scrape with the last known-good backup
./scripts/backup_scraper_data.sh --compare \
    data/raw/backups/bfo_odds_LAST_KNOWN_GOOD.jsonl \
    data/raw/bfo_odds_batch.jsonl
```

#### Method 2: Manual Spot Check
```bash
# Check for suspicious odds in current data
grep -c "+3400\|-10000" data/raw/bfo_odds_batch.jsonl

# If count > 0, you have a regression!
```

#### Method 3: Sample Validation
```bash
# Check a known fight's odds (UFC 297 main event)
grep "Dricus Du Plessis.*Sean Strickland" data/raw/bfo_odds_batch.jsonl | \
    jq '.odds.bookmakers[] | select(.bookmaker_id == 21)'

# Expected (correct closing odds):
# "fighter_1_odds": "-108▲"
# "fighter_2_odds": "-108▼"

# Regression (opening odds):
# "fighter_1_odds": "+3400▼"  # WRONG!
# "fighter_2_odds": "-200▼"    # WRONG!
```

## Workflow Recommendations

### Before Scraping

```bash
# 1. Backup current data
./scripts/backup_scraper_data.sh

# 2. Note the backup timestamp for later reference
# data/raw/backups/bfo_odds_YYYYMMDD_HHMMSS.jsonl
```

### During Scraping

```bash
# The scraper will append/overwrite data/raw/bfo_odds_batch.jsonl
make scrape-odds-optimized
```

### After Scraping

```bash
# 1. Spot check recent scrape results
make scrape-odds-optimized  # Still running...
# (Use the spot check commands from earlier in conversation)

# 2. When complete, create a backup
./scripts/backup_scraper_data.sh

# 3. Compare with previous backup to detect regressions
./scripts/backup_scraper_data.sh --compare \
    data/raw/backups/bfo_odds_PREVIOUS.jsonl \
    data/raw/bfo_odds_batch.jsonl

# 4. If regression detected, restore known-good backup
cp data/raw/backups/bfo_odds_KNOWN_GOOD.jsonl data/raw/bfo_odds_batch.jsonl
```

## File Locations

### Live Data
- **Current scraping output**: `data/raw/bfo_odds_batch.jsonl`
- **Progress tracking**: `data/raw/.scrape_progress.json`

### Backups
- **Backup directory**: `data/raw/backups/`
- **Naming format**: `bfo_odds_YYYYMMDD_HHMMSS.jsonl`
- **Metadata format**: `bfo_odds_YYYYMMDD_HHMMSS.meta.json`

### Historical/Archive
- **Old incorrect data**: `data/raw/backup_incorrect_odds/` (pre-fix backups)

## Scraper Version History

### v1 - closing_odds_fix_v1 (2025-11-12)
**Fix**: Changed `if (parsed.length >= 3)` to `if (parsed.length === 3)` in `scraper/spiders/bestfightodds_odds_final.py:171`

**Impact**:
- **Before**: Extracted opening/historical odds (+3400/-10000)
- **After**: Extracts only closing odds (-108/-108)

**Verification**: UFC 297 - Dricus vs Sean
- Old (wrong): FanDuel +3400/-200
- New (correct): FanDuel -108/-108

## Troubleshooting

### Issue: Backup script fails with "No data file found"
**Solution**: Scraper hasn't created output yet. Run scraper first:
```bash
make scrape-odds-recent-only  # Quick test
```

### Issue: Want to restore old backup
**Solution**: Copy backup to live location:
```bash
cp data/raw/backups/bfo_odds_TIMESTAMP.jsonl data/raw/bfo_odds_batch.jsonl
rm data/raw/.scrape_progress.json  # Clear progress to force re-scrape
```

### Issue: Accidentally overwrote good data
**Solution**: Check backups directory for most recent backup before the overwrite:
```bash
ls -lt data/raw/backups/
cp data/raw/backups/bfo_odds_LATEST_GOOD.jsonl data/raw/bfo_odds_batch.jsonl
```

## Best Practices

1. **Always backup before major scrapes**
2. **Spot check first 10-20 results** during long-running scrapes
3. **Compare backups** after completing a scrape
4. **Document scraper version** in backup metadata
5. **Keep at least 3 backups**: last known-good, previous, current
6. **Test scraper changes** on small datasets first (use `scrape-odds-recent-only`)

## Future Enhancements

Potential improvements to consider:

1. **Automatic backup on scrape start** (modify Makefile)
2. **Daily backup rotation** (keep last 7 days, last 4 weeks, etc.)
3. **Backup to cloud storage** (S3, Google Cloud Storage)
4. **Automated regression testing** (CI/CD integration)
5. **Data quality dashboard** (track odds distributions over time)

---

**Last Updated**: 2025-11-12
**Scraper Version**: closing_odds_fix_v1

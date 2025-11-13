# Betting Odds Scraper - Backup Quick Reference

## Quick Commands

### Before Running Scraper
```bash
# Backup current data
./scripts/backup_scraper_data.sh
```

### During/After Scraping
```bash
# Spot check for regressions (should return 0)
grep -c "+3400\|-10000" data/raw/bfo_odds_batch.jsonl

# View sample odds from recent scrape
tail -5 data/raw/bfo_odds_batch.jsonl | jq -c '{f1: .fighter_1.name, f2: .fighter_2.name, fanduel: [.odds.bookmakers[] | select(.bookmaker_id == 21)] | .[0]}'
```

### List Backups
```bash
./scripts/backup_scraper_data.sh --list
```

### Compare for Regressions
```bash
./scripts/backup_scraper_data.sh --compare \
    data/raw/backups/OLD_BACKUP.jsonl \
    data/raw/bfo_odds_batch.jsonl
```

### Restore Backup
```bash
# Copy backup to live location
cp data/raw/backups/bfo_odds_TIMESTAMP.jsonl data/raw/bfo_odds_batch.jsonl

# Clear progress to force fresh scrape
rm -f data/raw/.scrape_progress.json
```

## Regression Indicators

✅ **Good odds** (closing odds):
- FanDuel: -108/-108, -115/-105, +200/-250
- Range: typically -500 to +500

❌ **Bad odds** (opening/historical):
- FanDuel: +3400/-200, +1400/-10000
- Extreme values: > +1000 or < -1000 (usually regression)

## See Full Documentation
- `docs/ODDS_SCRAPER_DATA_PRESERVATION.md`

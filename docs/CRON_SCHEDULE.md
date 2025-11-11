# Automated Location Data Refresh - Cron Schedule

This document describes the recommended cron schedule for keeping fighter location data fresh and up-to-date.

## Overview

The location data refresh system uses a **priority-based scheduling** approach to ensure high-value fighters (active, winning streak) are updated more frequently than retired/historical fighters.

## Priority Levels

### High Priority
- **Fighters:** Active fighters with winning streak (fought in last 6 months + positive streak)
- **Refresh frequency:** Daily
- **Typical count:** ~100-200 fighters
- **Rationale:** These are the most visible fighters who fans are actively following

### Medium Priority
- **Fighters:** Recent fighters who fought in the last year (but not necessarily active/winning)
- **Refresh frequency:** Weekly
- **Typical count:** ~500-800 fighters
- **Rationale:** Still relevant fighters with potential for upcoming bookings

### Low Priority
- **Fighters:** Historical/retired fighters (last fought >1 year ago)
- **Refresh frequency:** Quarterly (every 3 months)
- **Typical count:** ~2,000+ fighters
- **Rationale:** Data rarely changes, but good to catch any corrections

### All Fighters
- **Full refresh:** Monthly check for stale data (>90 days old)
- **Rationale:** Catch any fighters that slipped through priority filters

---

## Recommended Cron Schedule

Add these entries to your crontab (`crontab -e`):

```bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UFC POKEDEX - LOCATION DATA REFRESH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Daily: Refresh high-priority fighters (active, winning streak)
# Runs at 2:00 AM daily
0 2 * * * cd /path/to/ufc-pokedex && make refresh-locations-high-priority >> /var/log/ufc-pokedex/refresh-high.log 2>&1

# Weekly: Refresh medium-priority fighters (recent fighters)
# Runs at 3:00 AM every Sunday
0 3 * * 0 cd /path/to/ufc-pokedex && make refresh-locations-medium-priority >> /var/log/ufc-pokedex/refresh-medium.log 2>&1

# Monthly: Refresh all stale data (>90 days old)
# Runs at 4:00 AM on the 1st of each month
0 4 1 * * cd /path/to/ufc-pokedex && make refresh-locations-all >> /var/log/ufc-pokedex/refresh-all.log 2>&1

# Daily: Monitor location data health
# Runs at 5:00 AM daily, exits with code 1 if issues detected
0 5 * * * cd /path/to/ufc-pokedex && make monitor-location-health >> /var/log/ufc-pokedex/health.log 2>&1

# Weekly: Apply manual overrides (if any new ones added)
# Runs at 6:00 AM every Monday
0 6 * * 1 cd /path/to/ufc-pokedex && make apply-location-overrides >> /var/log/ufc-pokedex/overrides.log 2>&1
```

### Important Notes

1. **Replace `/path/to/ufc-pokedex`** with your actual project directory
2. **Create log directory:** `mkdir -p /var/log/ufc-pokedex`
3. **Ensure cron has access to `.venv`** (virtual environment must be activated)
4. **Database must be accessible** from the cron user's environment
5. **Consider timezone:** Adjust times based on your server's timezone

---

## Alternative Schedule (Conservative)

If you want to be more conservative with server resources:

```bash
# Weekly: High-priority fighters only
0 2 * * 0 cd /path/to/ufc-pokedex && make refresh-locations-high-priority

# Monthly: Medium-priority fighters
0 3 1 * * cd /path/to/ufc-pokedex && make refresh-locations-medium-priority

# Quarterly: All fighters (every 3 months)
0 4 1 */3 * cd /path/to/ufc-pokedex && make refresh-locations-all
```

---

## Environment Variables for Cron

If your cron environment doesn't have access to your `.env` file, you may need to set environment variables explicitly:

```bash
# Option 1: Source environment file in cron command
0 2 * * * cd /path/to/ufc-pokedex && . .env && make refresh-locations-high-priority

# Option 2: Add environment variables to crontab header
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/ufc_pokedex
REDIS_URL=redis://localhost:6379/0

0 2 * * * cd /path/to/ufc-pokedex && make refresh-locations-high-priority
```

---

## Monitoring & Alerts

### Health Monitoring

The `monitor-location-health` command checks for:
- ✅ Coverage targets (60%+ birthplace, 80%+ nationality)
- ⚠️  Stale data warnings (>100 fighters with data >90 days old)
- ⚠️  Manual review queue (>50 fighters flagged)
- ⚠️  Never scraped fighters (>500)

### Exit Codes

- **0:** All checks passed (healthy)
- **1:** Issues detected (requires attention)

### Setting Up Email Alerts

You can configure cron to email you when issues are detected:

```bash
# Add MAILTO to crontab
MAILTO=your-email@example.com

# Use --exit-code flag to trigger email on failures
0 5 * * * cd /path/to/ufc-pokedex && .venv/bin/python scripts/monitor_location_data_health.py --exit-code
```

Or use a custom alert script:

```bash
#!/bin/bash
# /path/to/ufc-pokedex/scripts/health_check_with_alerts.sh

cd /path/to/ufc-pokedex
.venv/bin/python scripts/monitor_location_data_health.py --json > /tmp/health.json

if [ $? -ne 0 ]; then
  # Send alert (e.g., Slack webhook, email, PagerDuty)
  curl -X POST -H 'Content-type: application/json' \
    --data @/tmp/health.json \
    https://hooks.slack.com/services/YOUR/WEBHOOK/URL
fi
```

---

## Change Logs

All location changes are automatically logged to:
```
data/logs/location_changes_YYYY-MM-DD.jsonl
```

Each entry contains:
- `timestamp`: When the change was detected
- `fighter_id`: UFCStats fighter ID
- `fighter_name`: Fighter name
- `field`: What field changed (birthplace, training_gym, etc.)
- `old_value`: Previous value
- `new_value`: New value
- `source`: Where the data came from (ufc.com)
- `confidence`: Match confidence score (0-100)

### Log Rotation

Recommended log rotation policy:

```bash
# /etc/logrotate.d/ufc-pokedex
/path/to/ufc-pokedex/data/logs/*.jsonl {
    daily
    rotate 90
    compress
    delaycompress
    notifempty
    missingok
}
```

---

## Manual Commands

### Preview Refresh (Dry Run)
```bash
# See what would be refreshed without making changes
make refresh-locations-dry-run
```

### Refresh Specific Priority
```bash
# High priority only
make refresh-locations-high-priority

# Medium priority only
make refresh-locations-medium-priority

# All stale data
make refresh-locations-all
```

### Check Health
```bash
# Human-readable report
make monitor-location-health

# JSON output (for scripts/monitoring)
make monitor-location-health-json
```

### Apply Manual Overrides
```bash
# Preview overrides
make apply-location-overrides-dry-run

# Apply overrides
make apply-location-overrides
```

---

## Performance Considerations

### Estimated Run Times

- **High priority (100 fighters):** ~5-8 minutes
  - Rate limited: 2.5 seconds per fighter
  - With network delays: ~3-4 seconds per fighter

- **Medium priority (200 fighters):** ~10-15 minutes

- **All stale data (1000+ fighters):** ~45-60 minutes
  - Run during off-peak hours (2-6 AM)

### Resource Usage

- **CPU:** Low (mostly I/O wait)
- **Memory:** ~50-100 MB per script run
- **Network:** 1-2 KB per fighter (UFC.com HTML page)
- **Database:** Minimal (batch commits every 10 fighters)

### Rate Limiting

The refresh script respects UFC.com with:
- 2.5 second delay between requests (default)
- AutoThrottle enabled (adapts to server speed)
- Exponential backoff on errors
- Polite User-Agent header

---

## Troubleshooting

### Cron Not Running

**Check cron logs:**
```bash
grep CRON /var/log/syslog
# or
tail -f /var/log/cron
```

**Verify cron has correct environment:**
```bash
# Add to crontab for debugging
* * * * * env > /tmp/cron-env.txt
```

### Database Connection Errors

**Ensure DATABASE_URL is set:**
```bash
# In crontab
DATABASE_URL=postgresql+psycopg://...

# Or source .env file
0 2 * * * cd /path/to/ufc-pokedex && . .env && make refresh-locations-high-priority
```

### Script Failures

**Check logs:**
```bash
tail -f /var/log/ufc-pokedex/refresh-high.log
```

**Test script manually:**
```bash
cd /path/to/ufc-pokedex
.venv/bin/python scripts/refresh_fighter_locations.py --priority high --dry-run --limit 5
```

### UFC.com Rate Limiting

If you see many 429 errors:
1. Increase `DOWNLOAD_DELAY` in scraper settings
2. Reduce `--limit` in cron commands
3. Spread out refresh times (don't run all at once)

---

## Production Deployment Checklist

- [ ] Set up crontab with appropriate schedule
- [ ] Create log directory: `/var/log/ufc-pokedex/`
- [ ] Set up log rotation (logrotate config)
- [ ] Test each command manually first
- [ ] Configure email alerts for health monitoring
- [ ] Set up Slack/PagerDuty alerts (optional)
- [ ] Document custom overrides in `data/manual/location_overrides.json`
- [ ] Verify `.venv` is accessible to cron user
- [ ] Ensure database is accessible from cron environment
- [ ] Test dry-run mode for each priority level
- [ ] Monitor first few runs to ensure success

---

## Contact & Support

For issues or questions:
1. Check logs in `data/logs/` and `/var/log/ufc-pokedex/`
2. Run health check: `make monitor-location-health`
3. Review change logs for unexpected modifications
4. File an issue on GitHub (if applicable)

---

**Last Updated:** 2025-11-11
**Version:** 1.0

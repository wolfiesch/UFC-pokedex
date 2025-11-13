# Next Session Quick Start

**Last Updated:** November 12, 2025, 2:50 AM

---

## 🚀 Quick Status Check

Run this first:
```bash
/tmp/check_slug_progress.sh
```

---

## 📊 Current Background Processes

### 1. Slug Generation (Should be running)
**Check if running:**
```bash
ps aux | grep generate_all_slugs | grep -v grep
```

**If NOT running, restart:**
```bash
nohup bash -c "DATABASE_URL=postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex \
PYTHONPATH=. .venv/bin/python /tmp/generate_all_slugs.py > /tmp/slug_generation.log 2>&1" &
```

**View progress:**
```bash
tail -f /tmp/slug_generation.log
```

---

## ✅ Once Slugs are Complete (Expected: ~6:30 AM)

### Step 1: Verify Completion
```bash
PGPASSWORD=ufc_pokedex psql -h localhost -U ufc_pokedex -d ufc_pokedex -c \
  "SELECT COUNT(*) FILTER (WHERE ufc_com_slug IS NOT NULL) as with_slug FROM fighters;"
```

Expected: ~2,000-3,000 slugs (50-70% success rate)

### Step 2: Run Location Data Scraping

**High-priority fighters first (100 fighters, ~20 min):**
```bash
DATABASE_URL=postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex \
PYTHONPATH=. .venv/bin/python scripts/refresh_fighter_locations.py \
  --priority high --limit 100
```

**All fighters with slugs (~8-12 hours):**
```bash
nohup bash -c "DATABASE_URL=postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex \
PYTHONPATH=. .venv/bin/python scripts/refresh_fighter_locations.py \
  --priority all > /tmp/location_scraping.log 2>&1" &
```

### Step 3: Verify Location Data
```bash
# Check coverage
PGPASSWORD=ufc_pokedex psql -h localhost -U ufc_pokedex -d ufc_pokedex -c "
SELECT
  COUNT(*) as total,
  COUNT(birthplace) as with_birthplace,
  COUNT(nationality) as with_nationality,
  COUNT(training_gym) as with_gym
FROM fighters;"

# Test API
curl -s "http://localhost:8000/stats/countries?group_by=nationality" | python3 -m json.tool

# Test frontend
open http://localhost:3000/explore
```

---

## 🔧 If Services Need Restarting

```bash
# PostgreSQL + Redis
docker-compose ps
docker-compose up -d  # if not running

# Backend
make api  # or ctrl+c existing and restart

# Frontend
cd frontend
npm run dev
```

---

## 📝 Important Files

- **Status report:** `POST_MERGE_STATUS.md`
- **Slug generation script:** `/tmp/generate_all_slugs.py`
- **Progress checker:** `/tmp/check_slug_progress.sh`
- **Logs:** `/tmp/slug_generation.log`
- **Change logs:** `data/logs/location_changes_2025-11-12.jsonl`

---

## 🎯 Success Criteria

After location scraping completes, you should see:

✅ `/explore` page shows comprehensive country statistics
✅ Birthplace card shows multiple countries with fighter counts
✅ Nationality card shows multiple countries with fighter counts
✅ Database has 40-60% location coverage
✅ No "No data available" messages

---

## 🐛 Quick Troubleshooting

**Backend not connecting to PostgreSQL?**
```bash
docker-compose ps  # Check if db is running
```

**Scripts missing the PostgreSQL connection string?**
```bash
# Always prefix with DATABASE_URL:
DATABASE_URL=postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex \
PYTHONPATH=. .venv/bin/python scripts/your_script.py
```

**Slug generation stuck or failed?**
```bash
# Check last progress
tail -30 /tmp/slug_generation.log

# Check database
PGPASSWORD=ufc_pokedex psql -h localhost -U ufc_pokedex -d ufc_pokedex -c \
  "SELECT COUNT(*) FILTER (WHERE ufc_com_slug IS NOT NULL) as with_slug FROM fighters;"
```

---

## 📈 Expected Timeline

- **Slug generation:** Complete by ~6:30 AM (started 2:47 AM)
- **Location scraping (all):** 8-12 hours after slugs complete
- **Total:** ~15-18 hours from now

---

## 🔗 Key Endpoints

- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API Health: http://localhost:8000/health
- Location Stats: http://localhost:8000/stats/countries?group_by=nationality
- Explore Page: http://localhost:3000/explore

---

**End of Quick Start Guide**

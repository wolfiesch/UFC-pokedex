# UFC Pokedex - Bug Investigation Summary

**Date:** 2025-11-07 04:58 PST
**Method:** Playwright Web Automation
**Duration:** ~10 minutes
**Status:** ✅ Complete

---

## Quick Summary

✅ **Investigation Complete**
- **Bugs Found:** 1 Critical
- **Root Cause:** Identified
- **Fix Documented:** Yes
- **Estimated Fix Time:** 30-40 minutes

---

## Critical Finding

🔴 **Frontend using wrong API URL in local development**

**Problem:**
The frontend is calling `https://ufc.wolfgangschoenberger.com/api/*` (Cloudflare tunnel) instead of `http://localhost:8000/api/*` (local backend), causing all API requests to fail.

**Impact:**
- Search doesn't work
- Fighter details fail to load
- Events page empty
- Entire application non-functional in local dev

**Root Cause:**
`frontend/.env.local` has tunnel URLs instead of localhost URLs

**Quick Fix:**
```bash
# Edit frontend/.env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_ASSETS_BASE_URL=http://localhost:8000

# Restart frontend
cd frontend && pnpm dev
```

---

## What Was Tested

### Pages ✅
- Home page (/)
- Search functionality
- Fighter detail (/fighters/[id])
- Events (/events)
- Favorites (/favorites)

### Findings
- UI renders correctly
- Navigation works
- **API calls fail** (wrong URL configuration)
- Retry logic works (3 attempts before giving up)
- Error messages display correctly

---

## Documentation Generated

1. **BUG_REPORT.md** - Detailed bug documentation with screenshots
2. **BUG_FIX_PLAN.md** - Step-by-step implementation guide
3. **INVESTIGATION_SUMMARY.md** - This file

---

## Screenshots

Located in `.playwright-mcp/`:
- `01-home-page-initial.png` - Home page (working)
- `02-search-api-error.png` - Search failure
- `03-fighter-detail-api-errors.png` - Detail page errors
- `04-events-page-api-errors.png` - Events page empty
- `05-favorites-page.png` - Favorites page

---

## Next Steps

### Option 1: Quick Fix (5 minutes)
Manual edit of `frontend/.env.local` to use localhost URLs

### Option 2: Permanent Fix (30-40 minutes)
Update Makefile to auto-configure localhost URLs in `make dev-local`

**Recommended:** Do both - quick fix now, permanent fix when time permits

---

## Additional Notes

- Backend is running correctly on port 8000
- Frontend is running correctly on port 3000
- No code bugs found - pure configuration issue
- Documentation (CLAUDE.md) could be clearer about env switching

---

**For detailed information, see:**
- `BUG_REPORT.md` - Full bug details
- `BUG_FIX_PLAN.md` - Implementation guide

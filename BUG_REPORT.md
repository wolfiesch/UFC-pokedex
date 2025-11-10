# UFC Pokedex - Comprehensive Bug Report

**Latest Testing Date:** 2025-11-10
**Investigation Method:** Automated Playwright Browser Testing
**Environment:** Local development (make dev-local)
**Previous Report:** 2025-11-07

---

## Executive Summary

**UPDATED:** After fixing the critical configuration issue from 2025-11-07, comprehensive testing reveals the application's **core functionality is working well**. Identified 4 high-priority bugs related to React hydration, missing fighter images, rankings API failures, and 2 medium-priority warnings.

**Total Bugs Found:** 0 Critical, 4 High, 2 Medium, 0 Low

### Status Changes from Previous Report:
- ✅ **FIXED:** Frontend API configuration (was Critical, now resolved)
- ✅ **Working:** Search, Fighter Details, Events, Favorites all functional
- 🆕 **New Issues:** React hydration errors, missing images, rankings API errors

---

## Critical Issues (1)

### BUG #1: Frontend using wrong API base URL in local development

**Severity:** 🔴 CRITICAL
**Status:** Confirmed
**Affects:** All pages (Home, Search, Fighter Details, Events, Favorites)

#### Description
The frontend is configured to call `https://ufc.wolfgangschoenberger.com/api/*` (Cloudflare tunnel) instead of `http://localhost:8000/api/*` (local backend) when running `make dev-local`. This causes all API requests to fail with `ERR_FAILED` network errors.

#### Impact
- ❌ Search functionality completely broken
- ❌ Fighter detail pages fail to load data
- ❌ Events page shows "No events found" (API fails)
- ❌ Favorites page cannot sync with backend
- ❌ Fighter images fail to load
- ❌ Home page filters don't work properly

#### Root Cause
The file `frontend/.env.local` contains:
```env
NEXT_PUBLIC_API_BASE_URL=https://ufc.wolfgangschoenberger.com/api
NEXT_PUBLIC_ASSETS_BASE_URL=https://ufc.wolfgangschoenberger.com/api
```

This should be:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_ASSETS_BASE_URL=http://localhost:8000
```

#### Evidence
- **Screenshot 1:** `02-search-api-error.png` - Search fails with network errors
- **Screenshot 2:** `03-fighter-detail-api-errors.png` - Fighter detail page API failures
- **Screenshot 3:** `04-events-page-api-errors.png` - Events page shows no data

**Console Errors:**
```
[ERROR] Access to fetch at 'https://ufc.wolfgangschoenberger.com/api/search/?limit=20&offset=0&q=mcgregor' from origin 'http://localhost:3000' has been blocked by CORS policy
[ERROR] Failed to load resource: net::ERR_FAILED
[ERROR] API Error: GET [object Request] - [network_error] HTTP 500
```

#### Steps to Reproduce
1. Run `make dev-local` to start backend and frontend
2. Navigate to `http://localhost:3000`
3. Try to search for a fighter (e.g., "mcgregor")
4. Observe: Search fails with "Unable to load fighters" error
5. Open browser console: See multiple `ERR_FAILED` network errors
6. Check network tab: All requests going to `ufc.wolfgangschoenberger.com` instead of `localhost:8000`

#### Expected Behavior
When running `make dev-local`, all API calls should go to `http://localhost:8000` (local backend).

#### Actual Behavior
All API calls go to `https://ufc.wolfgangschoenberger.com/api` (Cloudflare tunnel), which fails.

#### Affected Code Files
- `frontend/.env.local` (lines 5, 8) - Incorrect configuration

#### Related Files
- `frontend/.env.example` - Shows correct localhost configuration
- `Makefile` - `dev-local` target should ensure localhost URLs

---

## Additional Observations

### Working Features ✅
- Home page UI loads correctly
- Navigation between pages works
- Fighter cards render with placeholder data
- Responsive design appears functional
- No JavaScript errors (only network failures)

### Documentation Issues 📝
The CLAUDE.md states:
> `make dev-local` - Start backend + frontend with localhost (recommended for local dev)

This implies that `make dev-local` should automatically configure localhost URLs, but it currently doesn't modify `frontend/.env.local` if it already exists with Cloudflare tunnel URLs.

---

## Screenshots

All screenshots saved to: `.playwright-mcp/`

1. `01-home-page-initial.png` - Home page loads successfully (no API calls yet)
2. `02-search-api-error.png` - Search functionality fails with API errors
3. `03-fighter-detail-api-errors.png` - Fighter detail page shows partial data with errors
4. `04-events-page-api-errors.png` - Events page empty due to API failures
5. `05-favorites-page.png` - Favorites page (no API calls on empty state)

---

## Test Coverage

### Pages Tested ✅
- ✅ Home page (/)
- ✅ Search functionality
- ✅ Fighter detail page (/fighters/[id])
- ✅ Events page (/events)
- ✅ Favorites page (/favorites)

### Features Tested ✅
- ✅ Navigation between pages
- ✅ Search input
- ✅ Fighter card display
- ✅ API error handling
- ✅ Console error monitoring

### Not Tested ⏭️
- Stats Hub page (/stats)
- FightWeb page (/fightweb)
- Random Fighter button
- Filter functionality (Division, Stance, etc.)
- Favorites management (add/remove)
- Event detail pages
- Mobile responsive testing (viewport resizing)

---

## Browser Console Summary

### Error Types Found
1. **CORS Errors:** Attempts to call Cloudflare tunnel from localhost origin
2. **Network Failures:** `net::ERR_FAILED` for all API endpoints
3. **Retry Logic:** API client retries 3 times before giving up
4. **Image Loading:** Fighter images fail to load from wrong base URL
5. **Favorites Sync:** "Failed to initialize favorites store" error

### Sample Error Log
```
[DEBUG] API Request: GET https://ufc.wolfgangschoenberger.com/api/search/?limit=20&offset=0&q=mcgregor
[ERROR] Access to fetch at 'https://ufc.wolfgangschoenberger.com/api/search/...' from origin 'http://localhost:3000' has been blocked
[WARNING] Retrying GET [object Request] (attempt 1/3)
[WARNING] Retrying GET [object Request] (attempt 2/3)
[WARNING] Retrying GET [object Request] (attempt 3/3)
[ERROR] API Error: GET [object Request] - [network_error] HTTP 500
```

---

## Recommendations

See `BUG_FIX_PLAN.md` for detailed fix implementation steps.

---

**Report Generated:** 2025-11-07 04:58 PST
**Investigation Time:** ~10 minutes
**Automation Tool:** Playwright MCP via Claude Code

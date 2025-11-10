# 🚀 Final Deployment Steps

## Current Status

### ✅ What's Been Fixed

All configuration files have been updated and pushed to GitHub:

1. **Railway Backend (`railway.json`)**
   - ✅ Fixed port binding to use `${PORT}` variable
   - ✅ Increased health check timeout to 300s
   - ✅ Simplified alembic command

2. **Vercel Frontend**
   - ✅ Moved `vercel.json` to `frontend/` directory
   - ✅ Simplified config to use Vercel auto-detection
   - ✅ Added `.vercelignore` to exclude large files

3. **Documentation**
   - ✅ Created `DEPLOYMENT.md` (comprehensive guide)
   - ✅ Created `DEPLOY_NOW.md` (quick start)
   - ✅ Created `.env.railway` (environment variables reference)

### ⚠️ Current Blockers

1. **Vercel:** Hit free tier limit (100 deployments/day) - wait 6 hours
2. **Railway:** Needs CORS environment variable set manually

---

## 🎯 Action Required (Do This Next!)

### Step 1: Set Railway CORS Variable (Do This Now!)

Railway needs the CORS environment variable to allow requests from Vercel.

**Option A: Via Railway Dashboard (Easiest)**

1. Go to: https://railway.app/dashboard
2. Select your **UFC-Pokedex** project
3. Click on your **service** (the one running the backend)
4. Go to **Variables** tab
5. Click **+ New Variable**
6. Add:
   - **Name:** `CORS_ALLOW_ORIGINS`
   - **Value:** `https://ufc-pokedex.vercel.app`
7. Click **Add**
8. Railway will automatically redeploy!

**Option B: Via Railway CLI**

```bash
# Login to Railway (opens browser)
railway login

# Link to your project
railway link
# Select: UFC-Pokedex

# Set the CORS variable
railway variables set CORS_ALLOW_ORIGINS=https://ufc-pokedex.vercel.app

# Deploy (if auto-deploy is not enabled)
railway up
```

**Verify Railway Deployment:**

Wait 2-3 minutes for the deployment, then test:

```bash
curl https://fulfilling-nourishment-production.up.railway.app/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "cache": "connected"
}
```

---

### Step 2: Set Vercel Environment Variable (Do This Now!)

Vercel needs to know your Railway backend URL.

**Via Vercel Dashboard:**

1. Go to: https://vercel.com/dashboard
2. Select **ufc-pokedex** project
3. Go to **Settings** → **Environment Variables**
4. Add new variable:
   - **Key:** `NEXT_PUBLIC_API_BASE_URL`
   - **Value:** `https://fulfilling-nourishment-production.up.railway.app`
   - **Environments:** Check all (Production, Preview, Development)
5. Click **Save**

**Via Vercel CLI:**

```bash
vercel env add NEXT_PUBLIC_API_BASE_URL
# When prompted, enter: https://fulfilling-nourishment-production.up.railway.app
# Select: Production, Preview, Development (all 3)
```

---

### Step 3: Deploy to Vercel (Wait 6 Hours First!)

You've hit Vercel's free tier limit (100 deployments/day). Wait 6 hours from your last deployment attempt.

**Check Time Remaining:**

```bash
vercel --prod
# Will show: "try again in X hours"
```

**When Limit Resets:**

**Option A: Auto-Deploy via GitHub (Recommended)**

If Vercel is connected to your GitHub repo, it will auto-deploy when you push. Since we already pushed the fixes:

1. Go to Vercel dashboard
2. Find the latest deployment
3. Click **Redeploy** when limit resets

**Option B: Manual Deploy**

```bash
vercel --prod
```

---

## 📋 Post-Deployment Checklist

Once both platforms are deployed:

### 1. Test Railway Backend

```bash
# Health check
curl https://fulfilling-nourishment-production.up.railway.app/health

# Get fighters
curl https://fulfilling-nourishment-production.up.railway.app/fighters/?limit=5
```

**Expected:**
- Health check returns `{"status": "healthy", ...}`
- Fighters endpoint returns JSON array

### 2. Test Vercel Frontend

```bash
# Open in browser
open https://ufc-pokedex.vercel.app
```

**Check:**
- ✓ Page loads without errors
- ✓ Fighter cards display
- ✓ Search works
- ✓ Click a fighter → detail page loads
- ✓ No CORS errors in browser console (F12)

### 3. End-to-End Test

1. Open https://ufc-pokedex.vercel.app
2. Search for a fighter (e.g., "McGregor")
3. Click on a fighter card
4. Verify:
   - ✓ Fighter details load
   - ✓ Fight history displays
   - ✓ No errors in browser console

---

## 🐛 Troubleshooting

### Railway Still Returns 502

**Check logs:**
```bash
railway logs | tail -50
```

**Common issues:**
- CORS not set → `railway variables | grep CORS`
- Database not connected → Check if PostgreSQL plugin is added
- Migrations failed → Look for Alembic errors in logs

**Fix:**
```bash
# Restart the service
railway restart

# Or redeploy
railway up
```

### Vercel Build Fails

**Check build logs:**
- Go to Vercel dashboard → Deployments → Click failed deployment → View build logs

**Common issues:**
- `NEXT_PUBLIC_API_BASE_URL` not set → Add in Vercel dashboard
- Build command failed → Verify `vercel.json` is in `frontend/` directory
- pnpm errors → Check if `pnpm-lock.yaml` exists in `frontend/`

### Frontend Shows No Data

**Check:**

1. Railway backend is responding:
   ```bash
   curl https://fulfilling-nourishment-production.up.railway.app/fighters/
   ```

2. CORS is configured:
   ```bash
   railway variables | grep CORS
   # Should show: CORS_ALLOW_ORIGINS=https://ufc-pokedex.vercel.app
   ```

3. Frontend has correct API URL:
   - Go to Vercel dashboard → Settings → Environment Variables
   - Verify `NEXT_PUBLIC_API_BASE_URL` is set

4. Check browser console (F12) for CORS errors

---

## 📊 Summary of Changes

| File | Change | Reason |
|------|--------|--------|
| `railway.json` | Use `${PORT}` instead of `8080` | Railway sets PORT dynamically |
| `railway.json` | Increase timeout to 300s | Migrations can take time |
| `vercel.json` | Moved to `frontend/` | Matches `rootDirectory` setting |
| `vercel.json` | Simplified config | Use Vercel auto-detection |
| `.vercelignore` | Created | Prevent uploading large files |
| `.env.railway` | Updated | Reference for required env vars |

---

## 🎯 Quick Command Reference

```bash
# Railway
railway login
railway link
railway variables set CORS_ALLOW_ORIGINS=https://ufc-pokedex.vercel.app
railway up
railway logs
railway status

# Vercel
vercel env add NEXT_PUBLIC_API_BASE_URL
vercel --prod
vercel logs <url>

# Testing
curl https://fulfilling-nourishment-production.up.railway.app/health
open https://ufc-pokedex.vercel.app
```

---

## ⏰ Timeline

1. **Now:** Set Railway CORS variable (via dashboard or CLI)
2. **Now:** Set Vercel environment variable (via dashboard or CLI)
3. **In 6 hours:** Deploy to Vercel (when free tier limit resets)
4. **After deployment:** Run verification checklist

---

## ✅ What Should Work

After completing all steps:

- ✅ Railway backend responds to health checks
- ✅ PostgreSQL database connected
- ✅ Redis cache connected (if plugin added)
- ✅ Migrations run automatically on deployment
- ✅ Vercel frontend builds successfully
- ✅ Frontend loads fighter data from Railway backend
- ✅ CORS allows cross-origin requests
- ✅ Search, filters, and detail pages work

---

Good luck! All the configuration issues are fixed. Just need to set those environment variables and wait for Vercel's deployment limit to reset! 🚀

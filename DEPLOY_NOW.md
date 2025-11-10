# 🚀 Deploy Your UFC Pokedex Now

I've fixed all the deployment configuration issues! Here's what to do next:

## What I Fixed

### ✅ Railway Backend (railway.json)
- Fixed port configuration to use Railway's `${PORT}` variable
- Increased health check timeout from 100s to 300s
- Simplified alembic command
- Updated .env.railway with correct environment variables

### ✅ Vercel Frontend (vercel.json)
- Removed redundant `cd frontend` commands (rootDirectory is already set)
- Fixed outputDirectory path
- Set correct Railway backend URL

### ✅ Created Deployment Documentation
- Comprehensive DEPLOYMENT.md guide
- Environment variables reference
- Troubleshooting tips

---

## 🔥 Deploy in 3 Steps

### Step 1: Deploy Railway Backend (5 minutes)

```bash
# 1. Login to Railway (opens browser)
railway login

# 2. Link to your existing project
railway link
# Select: UFC-Pokedex project

# 3. Verify PostgreSQL and Redis plugins are added
railway list
# You should see: PostgreSQL, Redis, and your service

# 4. Set CORS environment variable
railway variables set CORS_ALLOW_ORIGINS=https://ufc-pokedex.vercel.app

# 5. Deploy!
railway up

# 6. Watch logs to verify startup
railway logs
# Wait for: "Application startup complete"
```

**What to look for in logs:**
```
Running migrations...
Alembic upgrade head
INFO [alembic.runtime.migration] Running upgrade
Application startup complete
Uvicorn running on http://0.0.0.0:8080
```

### Step 2: Verify Railway Health (1 minute)

```bash
# Test the health endpoint
curl https://fulfilling-nourishment-production.up.railway.app/health

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "cache": "connected"
# }
```

If you get a 502 error, check logs:
```bash
railway logs | tail -50
```

### Step 3: Deploy Vercel Frontend (2 minutes)

```bash
# 1. Deploy to production
vercel --prod

# 2. Verify deployment
vercel ls
# Look for "✓ Ready" status
```

**Alternative: Push to GitHub**
If your Vercel project is connected to GitHub, just push:
```bash
git push origin master
```
Vercel will auto-deploy!

---

## ✅ Verification Checklist

After deployment, test these:

1. **Railway Health Check**
   ```bash
   curl https://fulfilling-nourishment-production.up.railway.app/health
   ```
   ✓ Should return `{"status": "healthy", ...}`

2. **Vercel Homepage**
   - Visit: https://ufc-pokedex.vercel.app
   - ✓ Fighter cards should load
   - ✓ Search should work

3. **API Integration**
   - Click on a fighter card
   - ✓ Detail page should load
   - ✓ Fight history should display

4. **CORS Working**
   - Open browser console (F12)
   - ✓ No CORS errors in console

---

## 🔧 If Something Goes Wrong

### Railway Returns 502

**Check logs:**
```bash
railway logs
```

**Common issues:**
1. **Migration failed** → Look for Alembic errors in logs
2. **Port binding failed** → Ensure PORT env var is set by Railway
3. **Database connection failed** → Verify PostgreSQL plugin is added

**Quick fix:**
```bash
# Restart the service
railway restart
```

### Vercel Build Fails

**Check build logs:**
```bash
vercel logs <deployment-url>
```

**Common issues:**
1. **pnpm install failed** → Check if pnpm-lock.yaml exists in frontend/
2. **Build command failed** → Verify rootDirectory is set to "frontend" in Vercel project settings
3. **API_BASE_URL not set** → Add env var in Vercel dashboard

**Quick fix:**
```bash
# Redeploy
vercel --prod
```

### Frontend Loads But Shows No Data

**Check:**
1. Railway backend is responding:
   ```bash
   curl https://fulfilling-nourishment-production.up.railway.app/fighters/
   ```

2. CORS is configured:
   ```bash
   railway variables | grep CORS
   ```

3. Frontend has correct API URL:
   ```bash
   vercel env ls | grep NEXT_PUBLIC_API_BASE_URL
   ```

---

## 🎯 Quick Deploy Commands Summary

```bash
# Railway
railway login
railway link
railway variables set CORS_ALLOW_ORIGINS=https://ufc-pokedex.vercel.app
railway up
railway logs

# Vercel
vercel --prod

# Test
curl https://fulfilling-nourishment-production.up.railway.app/health
open https://ufc-pokedex.vercel.app
```

---

## 📚 Need More Help?

- Full deployment guide: See `DEPLOYMENT.md`
- Railway docs: https://docs.railway.app
- Vercel docs: https://vercel.com/docs
- Check Railway dashboard: `railway open`
- Check Vercel dashboard: https://vercel.com/dashboard

---

## ⚡ Pro Tips

1. **Auto-deploy on Git push:**
   - Connect Railway to GitHub repo → auto-deploys on push to main
   - Connect Vercel to GitHub repo → auto-deploys on push to main

2. **Monitor deployments:**
   ```bash
   # Railway
   railway logs --follow

   # Vercel
   vercel logs <url> --follow
   ```

3. **Environment variables:**
   - Railway: `railway variables`
   - Vercel: `vercel env ls`

4. **Rollback if needed:**
   - Railway: `railway rollback`
   - Vercel: Redeploy previous deployment from dashboard

---

Good luck! 🚀 Your deployment configurations are now correct, so these commands should work smoothly.

# Railway Backend is Still Failing (502 Error)

## Current Issue

The Railway backend is returning **502 Bad Gateway**, which means the application is crashing on startup.

Even though CORS was set, there's likely another issue preventing the app from starting.

---

## How to Check Railway Logs

1. **Open Railway Dashboard:**
   ```bash
   open https://railway.app/dashboard
   ```

2. **Navigate to logs:**
   - Click **UFC-Pokedex** project
   - Click your **backend service** (not PostgreSQL or Redis)
   - Click **Deployments** tab
   - Click the **latest deployment** (top of the list)
   - You'll see the **Build Logs** and **Deploy Logs**

3. **Look for errors in Deploy Logs:**
   - Scroll through the logs
   - Look for red error messages
   - Common errors to look for:
     - `ModuleNotFoundError`
     - `alembic.util.exc.CommandError`
     - `sqlalchemy.exc.OperationalError`
     - `ConnectionRefusedError`
     - `Port already in use`

---

## Common Issues & Fixes

### Issue 1: Database Connection Failed

**Error in logs:**
```
sqlalchemy.exc.OperationalError: (psycopg.OperationalError) connection failed
```

**Fix:**
- Verify PostgreSQL plugin is added
- Check `DATABASE_URL` variable is set (should be auto-set by Railway)

### Issue 2: Migration Failed

**Error in logs:**
```
alembic.util.exc.CommandError: Can't locate revision identified by 'xyz'
```

**Fix:**
- Database schema is out of sync
- May need to reset database or run migrations manually

### Issue 3: Port Binding Failed

**Error in logs:**
```
[Errno 98] Address already in use
```

**Fix:**
- Should be fixed by our `${PORT}` variable update
- Verify railway.json has `--port ${PORT:-8080}`

### Issue 4: Missing Dependencies

**Error in logs:**
```
ModuleNotFoundError: No module named 'xxx'
```

**Fix:**
- Build failed to install dependencies
- Check if `uv sync` ran successfully in build logs

### Issue 5: Redis Connection Failed

**Error in logs:**
```
ConnectionRefusedError: [Errno 111] Connection refused (Redis)
```

**Fix:**
- This should NOT crash the app (backend is designed to degrade gracefully)
- But if it is, we need to make Redis connection optional

---

## Quick Diagnostic Commands

If you have Railway CLI set up:

```bash
# View recent logs
railway logs

# Check variables
railway variables

# Restart service
railway restart
```

---

## What I Need From You

Please check the Railway logs and tell me:

1. **What's in the Deploy Logs?**
   - Copy the last 20-30 lines of the logs
   - Especially any red error messages

2. **What's in the Build Logs?**
   - Did `uv sync` complete successfully?
   - Any errors during the build?

3. **What variables are set?**
   - Go to Variables tab
   - Verify these are set:
     - `DATABASE_URL` (auto-set by PostgreSQL plugin)
     - `REDIS_URL` (auto-set by Redis plugin)
     - `CORS_ALLOW_ORIGINS` (you set this)
     - `PORT` (auto-set by Railway)

---

## Alternative: Manual Deploy

If you want to try a manual redeploy:

1. **Via Dashboard:**
   - Deployments tab → Click latest deployment
   - Click **Redeploy** button

2. **Via CLI:**
   ```bash
   railway up
   ```

This will trigger a fresh deployment with the latest code from GitHub.

---

Let me know what you find in the logs, and I'll help diagnose the specific issue!

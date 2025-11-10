# Deployment Guide

## Railway Backend Deployment

### One-Time Setup

1. **Install Railway CLI** (if not installed):
   ```bash
   npm i -g @railway/cli
   railway login
   ```

2. **Initialize Railway Project**:
   ```bash
   railway init
   # Select: Create new project
   # Name: ufc-pokedex-backend
   ```

3. **Add PostgreSQL Plugin**:
   ```bash
   railway add --plugin postgresql
   ```

4. **Add Redis Plugin** (optional but recommended):
   ```bash
   railway add --plugin redis
   ```

5. **Set Environment Variables**:
   ```bash
   # Set CORS to allow your Vercel frontend
   railway variables set CORS_ALLOW_ORIGINS=https://ufc-pokedex.vercel.app
   railway variables set LOG_LEVEL=INFO
   ```

   Railway automatically sets:
   - `DATABASE_URL` (from PostgreSQL plugin)
   - `REDIS_URL` (from Redis plugin)
   - `PORT` (Railway's internal port)

### Deploy to Railway

```bash
# Deploy the backend
railway up

# Check deployment status
railway status

# View logs
railway logs

# Open Railway dashboard
railway open
```

### Verify Backend Health

```bash
# Get your Railway URL from dashboard or:
railway open

# Test health endpoint
curl https://your-project.railway.app/health
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

## Vercel Frontend Deployment

### One-Time Setup

1. **Install Vercel CLI** (if not installed):
   ```bash
   npm i -g vercel
   ```

2. **Link to Vercel Project**:
   ```bash
   vercel link
   # Follow prompts to create/link project
   ```

3. **Update Vercel Environment Variable**:
   
   Go to Vercel Dashboard → Project Settings → Environment Variables:
   
   - **Key:** `NEXT_PUBLIC_API_BASE_URL`
   - **Value:** `https://your-railway-backend.railway.app`
   - **Environment:** Production, Preview, Development

   Or via CLI:
   ```bash
   vercel env add NEXT_PUBLIC_API_BASE_URL
   # Enter: https://your-railway-backend.railway.app
   # Select: Production, Preview, Development
   ```

### Deploy to Vercel

```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

### Verify Frontend

Visit your Vercel deployment URL and check:
- Home page loads
- Fighter cards display
- Search works
- Fighter detail pages load

---

## Troubleshooting

### Railway Backend Issues

**502 Bad Gateway:**
- Check logs: `railway logs`
- Verify DATABASE_URL is set: `railway variables`
- Check migrations ran: Look for "Running migrations" in logs
- Verify port binding: App should bind to `0.0.0.0:${PORT}`

**Database Connection Failed:**
- Ensure PostgreSQL plugin is added: `railway list`
- Check DATABASE_URL format in logs
- Verify migrations completed successfully

**Application Crashes:**
- Check Python dependencies: `uv sync` should run in build
- Verify all required env vars are set
- Check for migration errors in startup logs

### Vercel Frontend Issues

**Build Failures:**
- Verify `rootDirectory` is set to `frontend` in Vercel project settings
- Check build logs in Vercel dashboard
- Ensure pnpm-lock.yaml exists in frontend directory

**API Connection Failed:**
- Verify `NEXT_PUBLIC_API_BASE_URL` is set correctly
- Check Railway backend is responding: `curl https://your-backend.railway.app/health`
- Verify CORS is configured on Railway with Vercel URL

**404 on Deployment:**
- Check outputDirectory is `.next` in vercel.json
- Verify build completed successfully in Vercel logs

---

## Environment Variables Summary

### Railway (Backend)

| Variable | Value | Auto-Set? |
|----------|-------|-----------|
| DATABASE_URL | `postgresql://...` | ✅ Yes (PostgreSQL plugin) |
| REDIS_URL | `redis://...` | ✅ Yes (Redis plugin) |
| PORT | `8080` or dynamic | ✅ Yes (Railway) |
| CORS_ALLOW_ORIGINS | `https://ufc-pokedex.vercel.app` | ❌ Manual |
| LOG_LEVEL | `INFO` | ❌ Manual |
| API_HOST | `0.0.0.0` | ❌ Optional (defaults to 0.0.0.0) |

### Vercel (Frontend)

| Variable | Value | Set Via |
|----------|-------|---------|
| NEXT_PUBLIC_API_BASE_URL | `https://your-backend.railway.app` | Dashboard or CLI |

---

## Post-Deployment Checklist

- [ ] Railway backend health check passes
- [ ] PostgreSQL connected (check `/health` response)
- [ ] Redis connected (check `/health` response)
- [ ] Vercel frontend builds successfully
- [ ] Frontend can fetch fighters from API
- [ ] Search functionality works
- [ ] Fighter detail pages load
- [ ] CORS allows requests from Vercel domain
- [ ] Production URLs updated in both platforms

---

## Useful Commands

```bash
# Railway
railway login
railway status
railway logs
railway variables
railway open

# Vercel
vercel login
vercel ls
vercel logs <deployment-url>
vercel env ls
vercel --prod

# Local Testing
make dev-local           # Test full stack locally
make api                 # Test backend only
make frontend            # Test frontend only
```

# cPanel Deployment - Final Steps

## ✅ What's Done:
1. Built Next.js app for production
2. Uploaded files to `/home/wolfdgpl/ufc-pokedex` via FTP
3. Configured Node.js app settings in cPanel

## ⏭️ Next Steps (You need to do these):

### Step 1: Install Dependencies on Server

**Via cPanel Terminal**:
1. Go to cPanel → **Advanced** → **Terminal**
2. Run:
```bash
cd /home/wolfdgpl/ufc-pokedex
rm -rf node_modules
npm install --production
```

### Step 2: Start the App

1. Go to cPanel → **Setup Node.js App**
2. Find `ufc-pokedex` in the list
3. Click **"Start App"** (or **"Restart App"** if already running)

###Step 3: Visit Your Site

**URL**: `https://wolfgangschoenberger.com/ufc`

## Environment Variables (Already Set):
- `NODE_ENV=production`
- `PORT=3000`
- `BASEPATH=/ufc`
- `NEXT_PUBLIC_API_BASE_URL=https://api.ufc.wolfgangschoenberger.com`

## Troubleshooting:

**"Module not found" errors**: Run `npm install` in Terminal (Step 1)

**404 on all pages**: Check `BASEPATH=/ufc` is set in environment variables

**API not working**: Make sure your local backend with Cloudflare Tunnel is running (`make dev`)

---

That's it! Once you complete Steps 1-3, your UFC Pokedex will be live at `wolfgangschoenberger.com/ufc`!

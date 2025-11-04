# UFC Pokedex - cPanel Deployment Guide

This guide covers deploying the UFC Pokedex frontend to a cPanel subdomain using SSH and Git.

## Overview

- **Deployment Method**: SSH + rsync (automated via bash script)
- **Build Type**: Static HTML export (Next.js static generation)
- **Target**: cPanel subdomain (e.g., `ufc.wolfgangschoenberger.com`)
- **Backend**: Separate deployment (not covered here - frontend only)

## Prerequisites

### 1. Find Your SSH Connection Details

You need to locate your cPanel SSH credentials from Namecheap:

#### SSH Hostname
Usually one of these:
- `wolfgangschoenberger.com`
- `ssh.wolfgangschoenberger.com`
- Or an IP address (check your Namecheap welcome email)

#### SSH Username
- Your cPanel username (found in Namecheap welcome email)
- Often the same as your domain name or a custom username

#### SSH Port
- Usually `22` (standard SSH port)
- Sometimes custom port like `2222` (check cPanel SSH/Shell Access settings)

#### How to Find in cPanel:
1. Log into cPanel
2. Search for "SSH Access" or "Terminal"
3. Look for connection details or enable SSH if disabled

### 2. SSH Key (Already Set Up)

Your SSH keys are stored in `.deployment/`:
- Private key: `.deployment/id_rsa` ✓
- Public key: `.deployment/id_rsa.pub` ✓

**Note**: Your private key is encrypted with a passphrase. You'll need this passphrase for deployment.

### 3. Create Subdomain in cPanel

Before deploying, you need to:

1. Log into cPanel
2. Go to **Domains** → **Subdomains**
3. Create a new subdomain: `ufc`
4. Set document root (e.g., `/home/username/public_html/ufc`)
5. Note the full path to this directory - you'll need it for deployment

## Quick Start

### 1. Create Deployment Configuration

```bash
make deploy-config
```

This creates `.deployment/config.env` from the template.

### 2. Edit Configuration

Edit `.deployment/config.env` with your actual values:

```bash
# SSH Connection Details
SSH_HOST=wolfgangschoenberger.com     # Your SSH hostname
SSH_USER=your_cpanel_username         # Your cPanel username
SSH_PORT=22                            # SSH port (usually 22)

# SSH Key Configuration
SSH_KEY_PATH=.deployment/id_rsa       # Path to your private key (already set)
SSH_KEY_PASSPHRASE=your_passphrase    # Your SSH key passphrase

# Deployment Paths (on cPanel server)
DEPLOY_PATH=/home/username/public_html/ufc    # Path from step 3 above
SUBDOMAIN=ufc.wolfgangschoenberger.com        # Your subdomain URL

# Production API Configuration
PROD_API_URL=https://api.ufc.wolfgangschoenberger.com   # Your backend API
```

### 3. Test SSH Connection

Before deploying, verify your SSH connection works:

```bash
# Test SSH connection manually
ssh -i .deployment/id_rsa -p 22 your_username@wolfgangschoenberger.com

# If successful, you should see the cPanel shell prompt
```

**Troubleshooting**:
- If prompted for passphrase: Enter your SSH key passphrase
- If "Permission denied": Check username and hostname
- If "Connection refused": Verify SSH is enabled in cPanel and port is correct
- If "Host key verification failed": Remove old host key with `ssh-keygen -R wolfgangschoenberger.com`

### 4. Deploy!

```bash
make deploy
```

This will:
1. Build the Next.js frontend as static HTML
2. Test SSH connection
3. Create deployment directory on server
4. Upload files via rsync
5. Display your live URL

## Deployment Commands

| Command | Description |
|---------|-------------|
| `make deploy-config` | Create deployment configuration file |
| `make deploy-build` | Build static export locally (test build) |
| `make deploy-test` | Build and preview locally on port 8080 |
| `make deploy` | Full deployment (build + upload to cPanel) |

## What Gets Deployed?

The deployment script:
- ✅ Builds `frontend/` as static HTML to `frontend/out/`
- ✅ Syncs `frontend/out/` to your cPanel subdomain directory
- ✅ Deletes removed files on server (`--delete` flag)
- ❌ Does NOT deploy backend (backend runs separately)
- ❌ Does NOT deploy `.env` files (excluded for security)

## Architecture Notes

### Frontend-Only Deployment

This deployment is **frontend-only**. The Next.js app is built as static HTML and served from cPanel.

**For the backend**, you have options:
1. Keep using Cloudflare Tunnel (current setup) pointing to your local backend
2. Deploy backend to a separate service (Heroku, Railway, DigitalOcean, etc.)
3. Use a serverless backend (Vercel Functions, Netlify Functions, etc.)

### Production vs Development

**Development** (local with Cloudflare Tunnel):
- Backend: `http://localhost:8000` → `https://api.ufc.wolfgangschoenberger.com`
- Frontend: `http://localhost:3000` → `https://ufc.wolfgangschoenberger.com`
- Uses `output: "standalone"` in `next.config.mjs`

**Production** (cPanel deployment):
- Backend: Your production API URL (set in `PROD_API_URL`)
- Frontend: Static HTML served from cPanel
- Uses `output: "export"` in `next.config.mjs`

The `next.config.mjs` automatically switches based on `BUILD_MODE` environment variable.

## SSL Certificate

After deployment, set up HTTPS in cPanel:

1. Go to **Security** → **SSL/TLS Status**
2. Find your subdomain `ufc.wolfgangschoenberger.com`
3. Click **Run AutoSSL** (free Let's Encrypt certificate)
4. Wait ~2 minutes for certificate installation
5. Test: `https://ufc.wolfgangschoenberger.com`

## Troubleshooting

### Build Errors

**"Module not found" errors:**
```bash
cd frontend
npm install
```

**Next.js build fails:**
- Check `frontend/out/` exists after `make deploy-build`
- Verify no hardcoded `localhost` URLs in code
- Check that `NEXT_PUBLIC_API_BASE_URL` is set correctly

### SSH Connection Issues

**"Permission denied (publickey)":**
- Verify SSH key is added to cPanel: cPanel → SSH Access → Manage SSH Keys
- Check private key permissions: `chmod 600 .deployment/id_rsa`
- Confirm SSH is enabled in cPanel

**"Connection refused":**
- SSH may not be enabled in cPanel (contact Namecheap support)
- Port may be different (try `2222` instead of `22`)

**"Host key verification failed":**
```bash
ssh-keygen -R wolfgangschoenberger.com
# Then try deploying again
```

### Deployment Issues

**Files not updating:**
- Clear browser cache (Cmd+Shift+R on Mac, Ctrl+F5 on Windows)
- Check cPanel File Manager to verify files were uploaded
- Verify `DEPLOY_PATH` points to correct subdomain directory

**404 errors after deployment:**
- Check subdomain document root in cPanel matches `DEPLOY_PATH`
- Verify index.html exists in deployment directory
- Check file permissions (should be 644 for files, 755 for directories)

**API calls failing:**
- Check `PROD_API_URL` in `.deployment/config.env`
- Verify backend is accessible from the deployed frontend
- Check browser console for CORS errors (backend needs to allow your subdomain)

### Backend CORS Configuration

Your backend must allow requests from your cPanel subdomain. Update `.env`:

```bash
# Add your cPanel subdomain to allowed origins
CORS_ALLOW_ORIGINS=https://ufc.wolfgangschoenberger.com
```

Restart backend after changing CORS settings.

## Manual Deployment (Alternative)

If the script fails, you can deploy manually:

```bash
# 1. Build frontend
cd frontend
BUILD_MODE=static npm run build:static

# 2. Upload to cPanel via SFTP
# Use FileZilla, Cyberduck, or command-line sftp
# Upload contents of frontend/out/ to your subdomain directory

# 3. Set permissions (if needed)
ssh -i .deployment/id_rsa user@host "chmod -R 755 /path/to/subdomain"
```

## Updating After First Deployment

After initial setup, deploying updates is simple:

```bash
# Make code changes
# ...

# Deploy
make deploy
```

The script will rebuild and sync only changed files.

## Security Notes

- ✅ `.deployment/` directory is in `.gitignore` (SSH keys never committed)
- ✅ Deployment script uses encrypted SSH key
- ✅ `.env` files are excluded from deployment
- ⚠️  Store `config.env` safely - it contains SSH credentials
- ⚠️  Never commit `.deployment/config.env` to version control

## Support

**Finding cPanel credentials:**
- Check your Namecheap welcome email
- Log into Namecheap → Server → Manage → cPanel login

**SSH not working:**
- Contact Namecheap support to enable SSH access
- Some shared hosting plans may restrict SSH

**Questions about this deployment:**
- Check `scripts/deploy.sh` for script details
- Review `next.config.mjs` for build configuration

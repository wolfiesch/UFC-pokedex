# SSH Deployment Setup for cPanel

## Current Status

You have SSH enabled on cPanel with the following details:
- **Server IP:** 162.254.39.96
- **Port:** 21098
- **Username:** wolfdgpl
- **Password:** EuroBender2024!

However, SSH password authentication is disabled on the server (security best practice). You need to use **SSH key authentication**.

## Option 1: Add Your SSH Key to cPanel (Recommended - Fast & Secure)

### Step 1: Copy Your Public Key

Your local public key is in `~/.ssh/id_ed25519.pub`. To view it:

```bash
cat ~/.ssh/id_ed25519.pub
```

### Step 2: Add Key to cPanel

1. Go to cPanel → **SSH Access** → **Manage SSH Keys**
2. Click **Import Key**
3. Give it a name (e.g., "macbook-deploy")
4. Paste your public key from Step 1
5. Click **Import**
6. Find the newly imported key and click **Manage** → **Authorize**

### Step 3: Test Connection

```bash
ssh -p 21098 wolfdgpl@162.254.39.96 'pwd'
```

If successful, you'll see `/home/wolfdgpl` printed.

### Step 4: Deploy!

Once SSH key authentication works, run:

```bash
make deploy-ssh
```

## Option 2: Generate New SSH Key for cPanel

If you prefer to use a separate key just for cPanel:

```bash
# Generate new key
ssh-keygen -t ed25519 -f ~/.ssh/cpanel_deploy -C "cpanel-deploy"

# View the public key
cat ~/.ssh/cpanel_deploy.pub

# Add to cPanel (same as Option 1, step 2)
# Then test with:
ssh -i ~/.ssh/cpanel_deploy -p 21098 wolfdgpl@162.254.39.96 'pwd'
```

## Option 3: Use FTP Deployment (Slower, but works now)

If you want to deploy immediately without SSH setup:

```bash
make deploy-ftp
```

This uses the FTP credentials and is slower but requires no additional configuration.

## What the SSH Deployment Does

When SSH is working, `make deploy-ssh` will:

1. Build Next.js for production with `/ufc` base path
2. Create a compressed archive of the build
3. Upload via SSH (much faster than FTP)
4. Extract on the server
5. You then just need to restart the Node.js app in cPanel

## Troubleshooting

### "Permission denied" error
- Your SSH key isn't authorized on the server
- Follow Option 1 or Option 2 above

### "Connection refused"
- SSH might be disabled temporarily
- Check cPanel → SSH Access → Enable SSH access

### "Port 21098 closed"
- Your hosting provider might have firewall rules
- Contact support or use FTP deployment

## Recommended Workflow

1. **One-time setup:** Add your SSH key to cPanel (Option 1)
2. **Every deploy:** Run `make deploy-ssh`
3. **In cPanel:** Restart Node.js app

This is much faster than FTP:
- FTP upload: ~5-10 minutes for all files
- SSH upload: ~30 seconds (compressed archive)

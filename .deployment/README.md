# Quick Deployment Reference

## Initial Setup (One-Time)

1. **Find SSH details in cPanel:**
   - Log into cPanel at your Namecheap hosting
   - Search for "SSH Access" or "Terminal"
   - Note: hostname, username, port (usually 22)

2. **Create subdomain in cPanel:**
   - Go to Domains → Subdomains
   - Create `ufc` subdomain
   - Note the document root path (e.g., `/home/username/public_html/ufc`)

3. **Configure deployment:**
   - Edit `.deployment/config.env` (already created)
   - Fill in your SSH details and paths
   - Save the file

4. **Test SSH connection:**
   ```bash
   ssh -i .deployment/id_rsa -p 22 your_user@your_host
   ```
   Enter your SSH key passphrase when prompted.

## Deployment Commands

```bash
# Full deployment (recommended)
make deploy

# Just build (test locally)
make deploy-build

# Preview build locally
make deploy-test   # Visit http://localhost:8080
```

## Files in This Directory

- `id_rsa` - Your SSH private key (encrypted, keep secure!)
- `id_rsa.pub` - Your SSH public key
- `config.env` - Your deployment settings (NEVER commit to git!)
- `config.env.example` - Template for reference

## What You Need to Provide

Edit `config.env` with these values:

```bash
SSH_HOST=____________              # e.g., wolfgangschoenberger.com
SSH_USER=____________              # Your cPanel username
SSH_KEY_PASSPHRASE=____________    # Your SSH key passphrase
DEPLOY_PATH=____________           # e.g., /home/user/public_html/ufc
PROD_API_URL=____________          # Your backend API URL
```

## Finding Information

**cPanel Login:**
- Namecheap dashboard → Server → Manage → cPanel

**SSH Username:**
- Check Namecheap welcome email
- Or: cPanel → Preferences → Change Password (shows username)

**Document Root Path:**
- cPanel → Domains → Subdomains
- Look at "Document Root" column for your subdomain

**SSH Port:**
- Usually 22
- If doesn't work, try 2222
- Or check: cPanel → Security → SSH Access

## Common Issues

**"Permission denied"**
- Verify SSH is enabled in cPanel
- Check if public key is added: cPanel → SSH Access → Manage SSH Keys

**"Connection refused"**
- SSH may not be enabled (contact Namecheap)
- Port may be wrong (try 2222)

**"Passphrase required"**
- Enter the passphrase you created when generating the SSH key
- If you forgot it, you'll need to generate new keys

## Help

Full documentation: `docs/deployment/DEPLOYMENT.md`

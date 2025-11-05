# 🚀 Quick Start: SSH Deployment

## Your Public SSH Key

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILpvSgKsobMjRLXZ+65f3xGf3A5t6wThWyqN9qVyILGB wolfgangs2000@gmail.com
```

## 3 Steps to Enable SSH Deployment

### 1. Add Key to cPanel (2 minutes)

1. Open cPanel → **SSH Access** → **Manage SSH Keys**
2. Click **"Import Key"**
3. Fill in:
   - **Name:** macbook-deploy
   - **Paste Public Key:** (paste the key above)
4. Click **Import**
5. Find "macbook-deploy" in the list
6. Click **"Manage"** → **"Authorize"**

### 2. Test Connection

```bash
ssh -p 21098 wolfdgpl@162.254.39.96 'pwd'
```

You should see: `/home/wolfdgpl`

### 3. Deploy!

```bash
make deploy-ssh
```

## What Happens Next

The script will:
1. ✅ Build Next.js (with `/ufc` base path)
2. ✅ Create compressed archive
3. ✅ Upload to server (~30 seconds)
4. ✅ Extract files

Then you just:
5. Go to cPanel → **Setup Node.js App**
6. Click **"Restart App"** on your ufc-pokedex application

Done! Visit: `https://wolfgangschoenberger.com/ufc`

---

## Alternative: Deploy with FTP Now

If you want to deploy immediately without SSH setup:

```bash
make deploy-ftp
```

This works right now but is slower (~5-10 min upload time).

---

## Files Created

- ✅ `scripts/deploy_ssh.sh` - SSH deployment script
- ✅ `SSH_SETUP.md` - Detailed SSH setup guide
- ✅ `Makefile` - Added `make deploy-ssh` and `make deploy-ssh-test`

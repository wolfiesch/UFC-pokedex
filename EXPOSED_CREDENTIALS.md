# 🔐 Exposed Credentials Summary

**⚠️ CRITICAL: All credentials listed below are COMPROMISED and must be changed immediately.**

---

## 🔴 Passwords (CHANGE IMMEDIATELY)

### SSH/FTP Password
- **Password:** `EuroBender2024!`
- **Used For:** 
  - SSH access to cPanel server
  - FTP access to hosting account
- **Exposed In:**
  - `.deployment/config.env` (Line 13)
  - `scripts/deploy_ssh.sh` (Line 18)
  - `scripts/deploy_cpanel.sh` (Line 28)
  - `docs/setup/SSH_SETUP.md` (Line 9)
  - `Makefile` (Line 783)
- **Action:** Change at hosting provider immediately

### Database Password (Development)
- **Password:** `ufc_pokedex`
- **Used For:** PostgreSQL development database
- **Exposed In:**
  - `.env.example` (Line 2)
  - `scripts/match_bfo_fighters.py` (Line 10)
  - `.github/workflows/test.yml`
- **Risk:** Medium (development only, not production)
- **Action:** Change if used in production

---

## 🔑 SSH Private Keys (REVOKE IMMEDIATELY)

### Key 1: id_rsa
- **File:** `.deployment/id_rsa`
- **Type:** OpenSSH Private Key (encrypted with passphrase)
- **Public Key:** `.deployment/id_rsa.pub`
- **Status:** ❌ COMPROMISED - Fully exposed in repository
- **Action:** 
  1. Revoke from all servers
  2. Delete files
  3. Generate new key

### Key 2: id_rsa_new
- **File:** `.deployment/id_rsa_new`
- **Type:** OpenSSH Private Key (no passphrase)
- **Public Key:** `.deployment/id_rsa_new.pub`
- **Comment:** `ufc-deployment`
- **Status:** ❌ COMPROMISED - Fully exposed in repository
- **Action:**
  1. Revoke from all servers
  2. Delete files
  3. Generate new key with passphrase

---

## 🌐 Server Access Details

### SSH Server
- **Hostname:** `server335.web-hosting.com`
- **IP Address:** `162.254.39.96`
- **Port:** `21098`
- **Username:** `wolfdgpl`
- **Auth Methods:** 
  - SSH Key (compromised keys above)
  - Password (compromised password above)
- **Exposed In:**
  - `.deployment/config.env`
  - `scripts/deploy_ssh.sh`
  - `docs/setup/SSH_SETUP.md`
  - `Makefile`

### FTP Server
- **Hostname:** `ftp.wolfgangschoenberger.com`
- **Port:** `21`
- **Username:** `claude@wolfgangschoenberger.com`
- **Password:** `EuroBender2024!` (same as SSH)
- **Exposed In:**
  - `.deployment/config.env`
  - `scripts/deploy_ftp.sh`

---

## 📁 Server Paths

### Deployment Directories
- **Path 1:** `/home/wolfdgpl/public_html/UFC`
- **Path 2:** `/home/wolfdgpl/ufc-pokedex`
- **Risk:** Attackers know exact directory structure
- **Exposed In:**
  - `.deployment/config.env`
  - `scripts/deploy_ssh.sh`
  - `scripts/deploy_cpanel.sh`
  - Documentation files

---

## 🌍 Domain Information

### Production Domains
- **Frontend:** `wolfgangschoenberger.com/ufc`
- **API:** `api.ufc.wolfgangschoenberger.com`
- **Alternative:** `ufc.wolfgangschoenberger.com`
- **Risk:** Low (publicly discoverable anyway)

---

## 📊 Exposure Timeline

### When Repository Became Public
- **Date:** 2025-11-13 (approximately)
- **Impact:** All credentials above have been publicly accessible since this date
- **Action Required:** Assume all credentials have been compromised

### How Long Credentials Were in Repository
- **SSH Keys:** Check `git log --all` for first commit
- **Passwords:** Check `git log --all` for first occurrence
- **Config Files:** Present since `.deployment/config.env` was added

---

## 🔍 Files Containing Credentials

### Configuration Files
1. `.deployment/config.env` ← **DELETE from git history**
   - SSH username, host, port
   - FTP username, password
   - Deployment paths
   - Production URLs

2. `frontend/.env.tunnel` ← **DELETE from git history**
   - Public URLs (less sensitive)

### Script Files (with hardcoded credentials)
1. `scripts/deploy_ssh.sh` ← **REDACT**
   - SSH password hardcoded (Line 18)
   - SSH host, port, username

2. `scripts/deploy_cpanel.sh` ← **REDACT**
   - FTP password fallback (Line 28)

3. `scripts/deploy_ftp.sh` ← **REVIEW**
   - Uses config.env (safer)

4. `Makefile` ← **REDACT**
   - SSH password in test command (Line 783)

### Documentation Files
1. `docs/setup/SSH_SETUP.md` ← **REDACT**
   - Full SSH credentials with password (Line 9)
   - IP address, port, username

2. `docs/setup/QUICKSTART_SSH.md` ← **REDACT**
   - SSH connection examples with real values

### SSH Key Files
1. `.deployment/id_rsa` ← **DELETE from git history**
2. `.deployment/id_rsa_new` ← **DELETE from git history**
3. `.deployment/id_rsa.pub` ← **DELETE from git history**
4. `.deployment/id_rsa_new.pub` ← **DELETE from git history**

---

## ⚡ Quick Action Commands

### 1. Change Passwords
```bash
# Log into cPanel at your hosting provider
# Navigate to: Security → Password & Security
# Change account password from: EuroBender2024!
# To: [Your new strong password]
```

### 2. Revoke SSH Keys
```bash
# Log into cPanel
# Navigate to: SSH Access → Manage SSH Keys
# Find and delete/deauthorize these keys:
# - Any key with comment "ufc-deployment"
# - Any keys you don't recognize
```

### 3. Generate New SSH Key
```bash
# Generate new key with passphrase
ssh-keygen -t ed25519 -f ~/.ssh/ufc_deploy_$(date +%Y%m%d) -C "ufc-deploy-new"

# View public key
cat ~/.ssh/ufc_deploy_*.pub

# Add to cPanel → SSH Access → Import Key → Authorize
```

### 4. Test New Key
```bash
# Test SSH connection (replace date with your key date)
ssh -i ~/.ssh/ufc_deploy_20251113 -p 21098 wolfdgpl@162.254.39.96 'pwd'

# Should output: /home/wolfdgpl
```

---

## 📋 Credential Rotation Checklist

After changing all credentials:

- [ ] SSH/FTP password changed at hosting provider
- [ ] Old SSH keys revoked in cPanel
- [ ] New SSH key generated (with passphrase)
- [ ] New SSH key authorized in cPanel
- [ ] New SSH key tested successfully
- [ ] Old password documented in password manager as "COMPROMISED - DO NOT USE"
- [ ] New credentials stored securely (password manager)
- [ ] Server logs reviewed for unauthorized access
- [ ] No unauthorized changes found on server
- [ ] All team members notified of credential rotation

---

## 🚨 Post-Rotation Actions

1. **Update Local Environment**
   ```bash
   # Create new config.env (don't commit!)
   cp .deployment/config.env.example .deployment/config.env
   # Edit with new values
   nano .deployment/config.env
   ```

2. **Update CI/CD Secrets** (if applicable)
   - GitHub Actions secrets
   - Other CI/CD platforms

3. **Document Incident**
   - When credentials were exposed
   - When they were rotated
   - Any suspicious activity found
   - Lessons learned

4. **Monitor for Abuse**
   - Check server logs daily for 1 week
   - Look for unusual access patterns
   - Monitor website for changes
   - Check for new files or users

---

## 📞 Emergency Contacts

If you detect unauthorized access:

1. **Hosting Provider Support**
   - Contact immediately to lock account
   - Request access logs
   - Request security audit

2. **Change All Related Passwords**
   - Email accounts
   - Domain registrar
   - Database accounts
   - Other services using same/similar passwords

3. **Backup and Restore**
   - If server is compromised, restore from known-good backup
   - Change all credentials before restoring

---

**Document Version:** 1.0  
**Created:** 2025-11-13  
**Status:** 🔴 CRITICAL - All credentials must be rotated IMMEDIATELY

**⚠️ After rotating all credentials, update this document with "ROTATED" status and dates.**

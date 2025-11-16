# Security Remediation Checklist

## 🚨 PHASE 1: EMERGENCY (Complete Within 1 Hour)

### Critical Password Changes
- [ ] **Change SSH/FTP password** `EuroBender2024!`
  - Log into your hosting provider (cPanel)
  - Navigate to Security → Password & Security
  - Change account password
  - Update all services using this password
  - Document new password in secure location (password manager)

### SSH Key Revocation
- [ ] **Revoke exposed SSH keys**
  - Log into cPanel → SSH Access → Manage SSH Keys
  - Remove/deauthorize:
    - Any key matching `.deployment/id_rsa.pub`
    - Any key matching `.deployment/id_rsa_new.pub`
  - Verify no other authorized keys are unknown

- [ ] **Generate new SSH keys (locally)**
  ```bash
  # DO NOT commit these!
  ssh-keygen -t ed25519 -f ~/.ssh/ufc_deploy_new -C "ufc-deploy-$(date +%Y%m%d)"
  # Add passphrase when prompted
  ```

- [ ] **Install new public key to cPanel**
  - Copy: `cat ~/.ssh/ufc_deploy_new.pub`
  - Add to cPanel → SSH Access → Import Key
  - Authorize the key

### Security Audit
- [ ] **Review server access logs**
  - Check SSH access logs: `/var/log/auth.log` or via cPanel
  - Look for suspicious IPs or timestamps
  - Check FTP access logs
  - Note: Repository was made public on 2025-11-13, check logs after this date

- [ ] **Verify server integrity**
  - Check for unauthorized files in `/home/wolfdgpl/`
  - Review recent file modifications
  - Check running processes
  - Verify no backdoors installed

- [ ] **Check for unauthorized changes**
  - Review website files for modifications
  - Check database for unusual activity
  - Review user accounts for unknown users

---

## 🔧 PHASE 2: CRITICAL FIXES (Complete Within 24 Hours)

### Remove Credentials from Files

- [ ] **Remove hardcoded passwords from scripts**
  - [ ] `scripts/deploy_ssh.sh` - Line 18
  - [ ] `scripts/deploy_cpanel.sh` - Line 28
  - [ ] `Makefile` - Line 783

- [ ] **Redact documentation**
  - [ ] `docs/setup/SSH_SETUP.md` - Lines 6-9
  - [ ] `docs/setup/QUICKSTART_SSH.md`

- [ ] **Delete sensitive files (locally first)**
  ```bash
  # Delete but don't commit yet
  rm .deployment/id_rsa
  rm .deployment/id_rsa_new
  rm .deployment/id_rsa.pub
  rm .deployment/id_rsa_new.pub
  rm .deployment/config.env
  rm frontend/.env.tunnel
  ```

### Update Configuration Files

- [ ] **Create template files**
  - [ ] Verify `.deployment/config.env.example` has no real credentials
  - [ ] Create `frontend/.env.tunnel.example` (copy from `.env.tunnel` but redact)

- [ ] **Update .gitignore** (already done)
  - [x] Add deployment secrets patterns
  - [x] Add SSH key patterns
  - [x] Add tunnel env patterns

- [ ] **Refactor deployment scripts**
  - [ ] Update `scripts/deploy_ssh.sh` to use env vars:
    ```bash
    SSH_PASSWORD="${SSH_PASSWORD:-}"
    if [ -z "$SSH_PASSWORD" ]; then
      echo "Error: SSH_PASSWORD not set"
      exit 1
    fi
    ```
  - [ ] Similar updates for `scripts/deploy_cpanel.sh`
  - [ ] Update `Makefile` to use env vars

### Clean Git History

⚠️ **WARNING:** This rewrites git history. Coordinate with team if applicable.

- [ ] **Install git-filter-repo**
  ```bash
  pip install git-filter-repo
  # or
  brew install git-filter-repo
  ```

- [ ] **Backup repository**
  ```bash
  cd ..
  cp -r UFC-pokedex UFC-pokedex-backup
  cd UFC-pokedex
  ```

- [ ] **Remove sensitive files from history**
  ```bash
  # Remove SSH private keys
  git filter-repo --path .deployment/id_rsa --invert-paths
  git filter-repo --path .deployment/id_rsa_new --invert-paths
  git filter-repo --path .deployment/id_rsa.pub --invert-paths
  git filter-repo --path .deployment/id_rsa_new.pub --invert-paths
  
  # Remove config with credentials
  git filter-repo --path .deployment/config.env --invert-paths
  
  # Remove tunnel env
  git filter-repo --path frontend/.env.tunnel --invert-paths
  ```

- [ ] **Force push cleaned history**
  ```bash
  # WARNING: This will rewrite history for all collaborators
  git push origin --force --all
  git push origin --force --tags
  ```

- [ ] **Notify collaborators**
  - [ ] Alert team about history rewrite
  - [ ] Provide instructions to re-clone:
    ```bash
    cd ..
    rm -rf UFC-pokedex
    git clone https://github.com/wolfiesch/UFC-pokedex
    ```

---

## 🛡️ PHASE 3: SECURITY HARDENING (Complete Within 1 Week)

### Implement Secret Detection

- [ ] **Enable GitHub Secret Scanning**
  - [ ] Go to Repository → Settings → Code security and analysis
  - [ ] Enable "Secret scanning"
  - [ ] Enable "Push protection"

- [ ] **Install pre-commit hooks**
  ```bash
  pip install pre-commit detect-secrets
  
  # Create .pre-commit-config.yaml (or update existing)
  cat >> .pre-commit-config.yaml << 'EOF'
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: package-lock.json|pnpm-lock.yaml|uv.lock
  EOF
  
  # Initialize
  detect-secrets scan > .secrets.baseline
  pre-commit install
  ```

- [ ] **Test pre-commit hooks**
  ```bash
  # Try to commit a fake secret - should be blocked
  echo "password=test123" > test.txt
  git add test.txt
  git commit -m "test"  # Should fail
  rm test.txt
  ```

### Create Security Documentation

- [ ] **Create SECURITY.md**
  ```markdown
  # Security Policy
  
  ## Supported Versions
  
  | Version | Supported          |
  | ------- | ------------------ |
  | main    | :white_check_mark: |
  
  ## Reporting a Vulnerability
  
  Please report security vulnerabilities to: [your-email@example.com]
  
  Do NOT create public issues for security vulnerabilities.
  
  ## Security Measures
  
  - All credentials managed via environment variables
  - SSH key authentication only (no passwords)
  - Pre-commit hooks for secret detection
  - Regular dependency updates via Dependabot
  ```

- [ ] **Update README.md**
  - [ ] Add security badge
  - [ ] Link to SECURITY.md
  - [ ] Document secure setup process

### Enable Dependency Scanning

- [ ] **Enable Dependabot**
  - [ ] Create `.github/dependabot.yml`:
    ```yaml
    version: 2
    updates:
      - package-ecosystem: "pip"
        directory: "/"
        schedule:
          interval: "weekly"
        open-pull-requests-limit: 10
        
      - package-ecosystem: "npm"
        directory: "/frontend"
        schedule:
          interval: "weekly"
        open-pull-requests-limit: 10
    ```

- [ ] **Enable Dependabot security updates**
  - [ ] Repository → Settings → Code security and analysis
  - [ ] Enable "Dependabot security updates"

### Secure Deployment Process

- [ ] **Use GitHub Secrets for CI/CD**
  - [ ] Repository → Settings → Secrets and variables → Actions
  - [ ] Add deployment secrets (if using GitHub Actions)

- [ ] **Document secure deployment**
  ```markdown
  ## Secure Deployment Setup
  
  1. Create `.env` file (never commit):
     ```bash
     cp .env.example .env
     # Edit .env with your values
     ```
  
  2. For deployment, set environment variables:
     ```bash
     export SSH_PASSWORD="your-password"
     export FTP_PASSWORD="your-password"
     make deploy
     ```
  
  3. Or use SSH key authentication (recommended):
     ```bash
     # No password needed
     make deploy-ssh
     ```
  ```

---

## 📊 PHASE 4: ONGOING MAINTENANCE

### Regular Security Audits

- [ ] **Monthly reviews**
  - [ ] Review access logs
  - [ ] Check for new security advisories
  - [ ] Update dependencies
  - [ ] Rotate credentials (quarterly)

- [ ] **Quarterly audits**
  - [ ] Full security scan
  - [ ] Review and revoke unused API keys
  - [ ] Check for exposed secrets
  - [ ] Review team access permissions

### Security Monitoring

- [ ] **Set up alerts**
  - [ ] GitHub Security Advisories
  - [ ] Dependabot alerts
  - [ ] Failed login attempts (hosting provider)

- [ ] **Regular backups**
  - [ ] Database backups
  - [ ] Configuration backups
  - [ ] Code backups (git is not a backup!)

### Best Practices Enforcement

- [ ] **Team training**
  - [ ] Never commit secrets
  - [ ] Use SSH keys, not passwords
  - [ ] Review PRs for security issues
  - [ ] Report security concerns immediately

- [ ] **Code review checklist**
  - [ ] No hardcoded credentials
  - [ ] Environment variables used correctly
  - [ ] No sensitive data in logs
  - [ ] Dependencies up to date

---

## ✅ Verification

After completing all phases, verify:

### Emergency Phase Verification
- [ ] New password works for SSH/FTP
- [ ] New SSH key works for authentication
- [ ] Old SSH keys no longer work
- [ ] No suspicious activity in logs
- [ ] Server files integrity verified

### Critical Fixes Verification
- [ ] No credentials in any tracked files
- [ ] `git log --all` shows no sensitive data
- [ ] `.gitignore` prevents future exposures
- [ ] Scripts use environment variables
- [ ] Documentation uses placeholders only

### Security Hardening Verification
- [ ] Pre-commit hooks block secrets
- [ ] GitHub Secret Scanning enabled
- [ ] Dependabot running
- [ ] SECURITY.md published
- [ ] README.md updated

### Final Security Check
- [ ] Run: `git log --all -p | grep -i "password\|secret\|token"` → Should find nothing
- [ ] Run: `detect-secrets scan` → Should pass
- [ ] Try committing fake secret → Should be blocked
- [ ] Check GitHub Security tab → Should show active scanning
- [ ] Review all open/closed issues → No exposed secrets

---

## 📞 Resources

- **Git Filter Repo:** https://github.com/newren/git-filter-repo
- **Detect Secrets:** https://github.com/Yelp/detect-secrets
- **GitHub Secret Scanning:** https://docs.github.com/en/code-security/secret-scanning
- **OWASP Security:** https://owasp.org/www-project-top-ten/
- **SSH Key Best Practices:** https://www.ssh.com/academy/ssh/keygen

---

## 🆘 If Compromised

If you discover unauthorized access:

1. **Immediately:**
   - Change all passwords
   - Revoke all SSH keys
   - Lock down server access
   - Take affected services offline if necessary

2. **Investigate:**
   - Review all server logs
   - Check for backdoors
   - Identify scope of breach
   - Document timeline

3. **Recover:**
   - Restore from clean backup
   - Rebuild if necessary
   - Implement additional security
   - Monitor for further attempts

4. **Report:**
   - Notify hosting provider
   - Report to relevant authorities if required
   - Notify users if data exposed
   - Document lessons learned

---

**Checklist Version:** 1.0  
**Last Updated:** 2025-11-13  
**Status:** 🔴 Action Required

#!/usr/bin/env bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# SSH Configuration (from cPanel screenshot)
SSH_HOST="162.254.39.96"
SSH_USER="wolfdgpl"
SSH_PORT="21098"
SSH_PASSWORD="EuroBender2024!"
DEPLOY_PATH="/home/wolfdgpl/ufc-pokedex"

echo -e "${GREEN}=== UFC Pokedex SSH Deployment ===${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  SSH Host: $SSH_HOST"
echo "  SSH Port: $SSH_PORT"
echo "  SSH User: $SSH_USER"
echo "  Deploy Path: $DEPLOY_PATH"
echo ""

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}Installing sshpass...${NC}"
    brew install hudochenkov/sshpass/sshpass
fi

# Create deployment archive
echo -e "${GREEN}[1/4] Building Next.js...${NC}"
cd "$FRONTEND_DIR"
BASEPATH=/ufc npm run build

echo ""
echo -e "${GREEN}[2/4] Creating deployment package...${NC}"
cd "$FRONTEND_DIR"
tar -czf /tmp/ufc-deploy.tar.gz \
    -C .next/standalone . \
    --exclude '.git' \
    --exclude 'node_modules/.cache'

# Add static files and server.js
tar -rzf /tmp/ufc-deploy.tar.gz \
    -C "$FRONTEND_DIR" \
    --transform 's,^.next/static,.next/static,' \
    .next/static

tar -rzf /tmp/ufc-deploy.tar.gz \
    -C "$FRONTEND_DIR" \
    server.js

echo ""
echo -e "${GREEN}[3/4] Uploading via SSH...${NC}"

# Upload archive
SSHPASS="$SSH_PASSWORD" sshpass -e scp -P "$SSH_PORT" \
    -o StrictHostKeyChecking=no \
    /tmp/ufc-deploy.tar.gz \
    "${SSH_USER}@${SSH_HOST}:/tmp/"

# Extract on server
echo ""
echo -e "${GREEN}[4/4] Deploying on server...${NC}"

SSHPASS="$SSH_PASSWORD" sshpass -e ssh -p "$SSH_PORT" \
    -o StrictHostKeyChecking=no \
    "${SSH_USER}@${SSH_HOST}" << 'ENDSSH'

# Create deployment directory
mkdir -p /home/wolfdgpl/ufc-pokedex
cd /home/wolfdgpl/ufc-pokedex

# Backup existing deployment
if [ -d ".next" ]; then
    echo "Creating backup..."
    rm -rf .next.backup
    mv .next .next.backup || true
fi

# Extract new deployment
echo "Extracting deployment package..."
tar -xzf /tmp/ufc-deploy.tar.gz

# Cleanup
rm /tmp/ufc-deploy.tar.gz

echo "Deployment extracted successfully!"
ls -la

ENDSSH

# Cleanup local archive
rm /tmp/ufc-deploy.tar.gz

echo ""
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Go to cPanel → Setup Node.js App"
echo "  2. Configure application:"
echo "     - Application root: ufc-pokedex"
echo "     - Application URL: /ufc"
echo "     - Application startup file: server.js"
echo "     - Node.js version: 20.x or higher"
echo "  3. Run 'npm install' in the cPanel terminal"
echo "  4. Start/Restart the app"
echo "  5. Visit: https://wolfgangschoenberger.com/ufc"
echo ""

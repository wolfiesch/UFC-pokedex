#!/usr/bin/env bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
DEPLOY_CONFIG="$PROJECT_ROOT/.deployment/config.env"

echo -e "${GREEN}=== UFC Pokedex FTP Deployment ===${NC}"
echo ""

# Check if config exists
if [ ! -f "$DEPLOY_CONFIG" ]; then
    echo -e "${RED}Error: Deployment config not found${NC}"
    exit 1
fi

source "$DEPLOY_CONFIG"

# Use FTP settings
FTP_HOST=${FTP_HOST:-$SSH_HOST}
FTP_USER=${FTP_USER:-$SSH_USER}
FTP_PASSWORD=${FTP_PASSWORD:-$SSH_KEY_PASSPHRASE}
FTP_PORT=${FTP_PORT:-21}

if [ -z "$FTP_HOST" ] || [ -z "$FTP_USER" ] || [ -z "$FTP_PASSWORD" ]; then
    echo -e "${RED}Error: FTP credentials not configured${NC}"
    exit 1
fi

STANDALONE_DIR="$FRONTEND_DIR/.next/standalone"
STATIC_DIR="$FRONTEND_DIR/.next/static"

echo -e "${YELLOW}Deployment Configuration:${NC}"
echo "  FTP Host: $FTP_HOST:$FTP_PORT"
echo "  FTP User: $FTP_USER"
echo "  Deploy Path: $DEPLOY_PATH"
echo ""

# Step 1: Build
echo -e "${GREEN}[1/3] Building Next.js for production...${NC}"
cd "$FRONTEND_DIR"

if [ -n "$PROD_API_URL" ]; then
    export NEXT_PUBLIC_API_BASE_URL="$PROD_API_URL"
fi

# Build with standalone output
BASEPATH=/ufc npm run build

if [ ! -d "$STANDALONE_DIR" ]; then
    echo -e "${RED}Error: Build failed - standalone output not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Build complete${NC}"
echo ""

# Step 2: Upload via lftp
echo -e "${GREEN}[2/3] Uploading files via FTP...${NC}"

if ! command -v lftp &> /dev/null; then
    echo -e "${YELLOW}Installing lftp...${NC}"
    brew install lftp
fi

# Create lftp script with longer timeout
cat > /tmp/lftp_script.txt <<EOF
set ftp:ssl-allow no
set ssl:verify-certificate no
set net:timeout 60
set net:reconnect-interval-base 5
set net:max-retries 3
open -u $FTP_USER,$FTP_PASSWORD -p $FTP_PORT $FTP_HOST
mkdir -p $DEPLOY_PATH
cd $DEPLOY_PATH
# Upload standalone contents (includes .next, node_modules, package.json)
mirror --reverse --delete --verbose --parallel=3 --exclude node_modules/.cache/ $STANDALONE_DIR/ ./
# Upload server.js (overwrite if exists)
put -O ./ $FRONTEND_DIR/server.js
# Upload static assets
mkdir -p .next/static
mirror --reverse --verbose --parallel=3 $STATIC_DIR/ ./.next/static/
bye
EOF

lftp -f /tmp/lftp_script.txt
rm /tmp/lftp_script.txt

echo ""
echo -e "${GREEN}✓ Upload complete!${NC}"
echo ""
echo -e "${YELLOW}[3/3] Next steps in cPanel:${NC}"
echo "  1. Go to cPanel → Setup Node.js App"
echo "  2. Configure application:"
echo "     - Application root: ufc-pokedex"
echo "     - Application URL: /ufc"
echo "     - Application startup file: server.js"
echo "  3. Click 'Run NPM Install' button"
echo "  4. Click 'Start App' or 'Restart App'"
echo ""
if [ -n "$SUBDOMAIN" ]; then
    echo -e "${GREEN}Your site will be live at: https://$SUBDOMAIN${NC}"
else
    echo -e "${GREEN}Your site will be live at: https://wolfgangschoenberger.com/ufc${NC}"
fi
echo ""

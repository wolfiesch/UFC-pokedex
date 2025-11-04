#!/usr/bin/env bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
DEPLOY_CONFIG="$PROJECT_ROOT/.deployment/config.env"

echo -e "${GREEN}=== UFC Pokedex cPanel Deployment ===${NC}"
echo ""

# Load config
if [ ! -f "$DEPLOY_CONFIG" ]; then
    echo -e "${RED}Error: config not found${NC}"
    exit 1
fi

source "$DEPLOY_CONFIG"

FTP_HOST=${FTP_HOST:-$SSH_HOST}
FTP_USER=${FTP_USER:-$SSH_USER}
FTP_PASSWORD=${FTP_PASSWORD:-EuroBender2024!}
DEPLOY_PATH=${DEPLOY_PATH:-/home/wolfdgpl/ufc-pokedex}

echo -e "${YELLOW}Configuration:${NC}"
echo "  FTP Host: $FTP_HOST"
echo "  FTP User: $FTP_USER"
echo "  Deploy Path: $DEPLOY_PATH"
echo ""

# Check if lftp is installed
if ! command -v lftp &> /dev/null; then
    echo -e "${YELLOW}Installing lftp...${NC}"
    brew install lftp
fi

# Upload via FTP
echo -e "${GREEN}[1/2] Uploading files via FTP...${NC}"

lftp -u "$FTP_USER,$FTP_PASSWORD" "$FTP_HOST" <<EOF
set ftp:ssl-allow no
set ssl:verify-certificate no
mkdir -p $DEPLOY_PATH
cd $DEPLOY_PATH
mirror --reverse --delete --verbose --exclude .git/ --exclude node_modules/.cache/ $FRONTEND_DIR/.next/standalone/ ./
put -O ./ $FRONTEND_DIR/server.js
mirror --reverse --verbose $FRONTEND_DIR/.next/static ./.next/static
mirror --reverse --verbose $FRONTEND_DIR/public ./public
bye
EOF

echo ""
echo -e "${GREEN}✓ Upload complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Go to cPanel → Setup Node.js App"
echo "  2. Find your 'ufc-pokedex' application"
echo "  3. Click 'Start App' or 'Restart App'"
echo "  4. Visit: https://wolfgangschoenberger.com/ufc"
echo ""

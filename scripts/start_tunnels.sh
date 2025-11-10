#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

TUNNEL_NAME="ufc-pokedex"
DOMAIN="wolfgangschoenberger.com"
FRONTEND_SUBDOMAIN="ufc.${DOMAIN}"
API_SUBDOMAIN="api.ufc.${DOMAIN}"

echo -e "${BLUE}Starting Cloudflare tunnel...${NC}"

# Kill any existing cloudflared processes
pkill cloudflared 2>/dev/null || true
sleep 1

# Check if tunnel is configured
CONFIG_FILE="$HOME/.cloudflared/config.yml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}✗ Tunnel not configured. Please run:${NC}"
    echo -e "${YELLOW}  bash scripts/setup_tunnel.sh${NC}"
    exit 1
fi

# Start the tunnel using the config file
echo -e "${YELLOW}Starting tunnel '${TUNNEL_NAME}'...${NC}"
cloudflared tunnel run "$TUNNEL_NAME" > /tmp/tunnel.log 2>&1 &
TUNNEL_PID=$!

# Wait for tunnel to establish
echo -e "${YELLOW}Waiting for tunnel to connect...${NC}"
sleep 5

# Check if tunnel is running
if ! ps -p $TUNNEL_PID > /dev/null 2>&1; then
    echo -e "${RED}✗ Tunnel failed to start. Check logs:${NC}"
    echo -e "${YELLOW}  /tmp/tunnel.log${NC}"
    cat /tmp/tunnel.log
    exit 1
fi

# Use the configured URLs (they're static based on DNS routes)
FRONTEND_URL="https://${FRONTEND_SUBDOMAIN}"
# Use direct API subdomain (no proxy needed - API tunnel works perfectly)
API_URL="https://${API_SUBDOMAIN}"

# Output URLs in machine-readable format (for Make to parse)
echo "FRONTEND_URL=$FRONTEND_URL"
echo "API_URL=$API_URL"

# Output human-readable success message
echo -e "${GREEN}✓ Tunnel started successfully!${NC}"
echo -e "${GREEN}  Tunnel PID: $TUNNEL_PID${NC}"

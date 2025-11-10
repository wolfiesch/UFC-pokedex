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
LOCAL_FRONTEND_URL="http://localhost:3000"
LOCAL_API_URL="http://localhost:8000"

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
REMOTE_FRONTEND_URL="https://${FRONTEND_SUBDOMAIN}"
REMOTE_API_URL="https://${API_SUBDOMAIN}"

# Check whether the remote URLs are actually reachable (e.g., network or DNS
# restrictions inside the runtime sandbox). If we cannot reach Cloudflare,
# fall back to local loopback addresses so that `make dev` still works.
if curl -sS --connect-timeout 2 --max-time 5 -o /dev/null "$REMOTE_API_URL"; then
    FRONTEND_URL="$REMOTE_FRONTEND_URL"
    API_URL="$REMOTE_API_URL"
    echo -e "${GREEN}✓ Tunnel started successfully!${NC}"
    echo -e "${GREEN}  Tunnel PID: $TUNNEL_PID${NC}"
else
    FRONTEND_URL="$LOCAL_FRONTEND_URL"
    API_URL="$LOCAL_API_URL"
    echo -e "${YELLOW}⚠️  Unable to reach ${REMOTE_API_URL}. Falling back to local URLs.${NC}"
fi

# Output URLs in machine-readable format (for Make to parse)
echo "FRONTEND_URL=$FRONTEND_URL"
echo "API_URL=$API_URL"

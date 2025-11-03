#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Cloudflare tunnels...${NC}"

# Kill any existing cloudflared processes
pkill cloudflared 2>/dev/null || true
sleep 1

# Start frontend tunnel (port 3000)
echo -e "${YELLOW}Starting frontend tunnel (port 3000)...${NC}"
cloudflared tunnel --url http://localhost:3000 > /tmp/tunnel-frontend.log 2>&1 &
FRONTEND_PID=$!

# Start API tunnel (port 8000)
echo -e "${YELLOW}Starting API tunnel (port 8000)...${NC}"
cloudflared tunnel --url http://localhost:8000 > /tmp/tunnel-api.log 2>&1 &
API_PID=$!

# Wait for tunnels to establish (they write URLs to logs)
echo -e "${YELLOW}Waiting for tunnels to establish...${NC}"
sleep 8

# Extract frontend URL
FRONTEND_URL=""
for i in {1..20}; do
    if grep -q "https://.*trycloudflare.com" /tmp/tunnel-frontend.log 2>/dev/null; then
        FRONTEND_URL=$(grep -o "https://[a-z0-9-]*\.trycloudflare\.com" /tmp/tunnel-frontend.log | head -1)
        break
    fi
    sleep 1
done

# Extract API URL
API_URL=""
for i in {1..20}; do
    if grep -q "https://.*trycloudflare.com" /tmp/tunnel-api.log 2>/dev/null; then
        API_URL=$(grep -o "https://[a-z0-9-]*\.trycloudflare\.com" /tmp/tunnel-api.log | head -1)
        break
    fi
    sleep 1
done

# Verify both URLs were found
if [ -z "$FRONTEND_URL" ] || [ -z "$API_URL" ]; then
    echo -e "${YELLOW}Warning: Could not extract tunnel URLs. Check logs:${NC}"
    echo "  Frontend: /tmp/tunnel-frontend.log"
    echo "  API: /tmp/tunnel-api.log"
    exit 1
fi

# Output URLs in machine-readable format (for Make to parse)
echo "FRONTEND_URL=$FRONTEND_URL"
echo "API_URL=$API_URL"

# Output human-readable success message
echo -e "${GREEN}✓ Tunnels started successfully!${NC}"
echo -e "${GREEN}  Frontend PID: $FRONTEND_PID${NC}"
echo -e "${GREEN}  API PID: $API_PID${NC}"

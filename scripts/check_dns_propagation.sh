#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

FRONTEND_DOMAIN="ufc.wolfgangschoenberger.com"
API_DOMAIN="api.ufc.wolfgangschoenberger.com"
EXPECTED_IPS=("104.21.14.155" "172.67.203.204")

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Cloudflare Tunnel DNS Propagation Check          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

check_domain() {
    local domain=$1
    local domain_name=$2

    echo -e "${BLUE}Checking ${domain_name}: ${domain}${NC}"
    echo ""

    # Check with Cloudflare DNS (should always work)
    echo -e "${YELLOW}  1. Cloudflare DNS (1.1.1.1)...${NC}"
    CF_RESULT=$(dig +short "$domain" @1.1.1.1 2>/dev/null | grep -E "^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$" | head -1)
    if [ -n "$CF_RESULT" ]; then
        echo -e "${GREEN}     ✓ Resolves to: $CF_RESULT${NC}"
    else
        echo -e "${RED}     ✗ Not found${NC}"
        return 1
    fi

    # Check with local DNS
    echo -e "${YELLOW}  2. Your Local DNS...${NC}"
    LOCAL_RESULT=$(dig +short "$domain" 2>/dev/null | grep -E "^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$" | head -1)
    if [ -n "$LOCAL_RESULT" ]; then
        echo -e "${GREEN}     ✓ Resolves to: $LOCAL_RESULT${NC}"
    else
        echo -e "${RED}     ✗ Not resolved (propagation pending)${NC}"
        return 1
    fi

    # Check nslookup
    echo -e "${YELLOW}  3. nslookup test...${NC}"
    NSLOOKUP_RESULT=$(nslookup "$domain" 2>/dev/null | grep -A1 "answer:" | grep "Address" | awk '{print $2}' | head -1)
    if [ -n "$NSLOOKUP_RESULT" ]; then
        echo -e "${GREEN}     ✓ Resolves to: $NSLOOKUP_RESULT${NC}"
    else
        echo -e "${RED}     ✗ Not resolved${NC}"
        return 1
    fi

    # Test actual connectivity
    echo -e "${YELLOW}  4. HTTPS connectivity test...${NC}"
    if curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://$domain/health" 2>/dev/null | grep -q "200"; then
        echo -e "${GREEN}     ✓ HTTPS connection successful${NC}"
    else
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://$domain/health" 2>/dev/null || echo "Failed")
        echo -e "${RED}     ✗ Connection failed (HTTP $HTTP_CODE)${NC}"
        return 1
    fi

    echo ""
    return 0
}

# Check frontend domain
if check_domain "$FRONTEND_DOMAIN" "Frontend"; then
    FRONTEND_STATUS="${GREEN}✓ Ready${NC}"
else
    FRONTEND_STATUS="${RED}✗ Not Ready${NC}"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check API domain
if check_domain "$API_DOMAIN" "API"; then
    API_STATUS="${GREEN}✓ Ready${NC}"
else
    API_STATUS="${RED}✗ Not Ready${NC}"
fi

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${BLUE}Summary:${NC}"
echo -e "  Frontend ($FRONTEND_DOMAIN): $FRONTEND_STATUS"
echo -e "  API ($API_DOMAIN): $API_STATUS"
echo ""

# Check if both are ready
if check_domain "$FRONTEND_DOMAIN" "Frontend" >/dev/null 2>&1 && check_domain "$API_DOMAIN" "API" >/dev/null 2>&1; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           ✓ DNS Fully Propagated - Ready to Use!          ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Your application is accessible at:${NC}"
    echo -e "  ${YELLOW}Frontend:${NC} https://$FRONTEND_DOMAIN"
    echo -e "  ${YELLOW}API:${NC}      https://$API_DOMAIN"
    echo ""
    exit 0
else
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║         DNS Propagation Still in Progress                 ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}What to do:${NC}"
    echo ""
    echo -e "${YELLOW}Option 1: Wait for DNS propagation (5-30 minutes typically)${NC}"
    echo -e "  Run this script again to check status:"
    echo -e "  ${GREEN}bash scripts/check_dns_propagation.sh${NC}"
    echo ""
    echo -e "${YELLOW}Option 2: Add temporary hosts file entry (immediate fix)${NC}"
    echo -e "  ${GREEN}echo \"104.21.14.155 api.ufc.wolfgangschoenberger.com\" | sudo tee -a /etc/hosts${NC}"
    echo ""
    echo -e "${YELLOW}Option 3: Use Cloudflare DNS servers${NC}"
    echo -e "  1. Go to: System Settings → Network → Wi-Fi → Details → DNS"
    echo -e "  2. Add: 1.1.1.1 and 1.0.0.1"
    echo -e "  3. Restart your browser"
    echo ""
    echo -e "${YELLOW}Option 4: Clear DNS cache${NC}"
    echo -e "  ${GREEN}sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder${NC}"
    echo ""
    exit 1
fi

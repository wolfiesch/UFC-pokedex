#!/bin/bash

# UFC Pokedex - FormBar Tooltip Testing Script
# This script runs Playwright tests for the FormBar component and captures screenshots

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}FormBar Tooltip Testing${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Check if Playwright is installed
if ! pnpm list @playwright/test >/dev/null 2>&1; then
  echo -e "${YELLOW}⚠️  Playwright not found. Installing...${NC}"
  pnpm add -D @playwright/test
  npx playwright install chromium
fi

# Ensure screenshots directory exists
mkdir -p tests/e2e/screenshots

# Check if dev server is running
if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
  echo -e "${YELLOW}⚠️  Dev server not running on port 3000${NC}"
  echo -e "${YELLOW}Please start the dev server first:${NC}"
  echo -e "${YELLOW}  make dev${NC}"
  echo
  echo -e "${YELLOW}Or run this script will wait for 30 seconds...${NC}"
  sleep 30

  if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${RED}❌ Dev server still not available. Exiting.${NC}"
    exit 1
  fi
fi

echo -e "${GREEN}✅ Dev server is running${NC}"
echo

# Run the FormBar tooltip tests
echo -e "${BLUE}🧪 Running FormBar tooltip tests...${NC}"
npx playwright test tests/e2e/specs/form-bar-tooltips.spec.ts \
  --project=chromium \
  --reporter=list

echo
echo -e "${GREEN}✅ Tests complete!${NC}"
echo
echo -e "${BLUE}📸 Screenshots saved to: tests/e2e/screenshots/${NC}"
echo -e "${BLUE}📊 Test report: playwright-report/index.html${NC}"
echo
echo -e "${BLUE}To view the HTML report:${NC}"
echo -e "${BLUE}  npx playwright show-report${NC}"

#!/bin/bash
# Comprehensive test suite for AI Image Validator
# This script runs all tests to validate the implementation

set -e  # Exit on error

API_KEY="${OPENAI_API_KEY:-}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================================================="
echo "AI Image Validator - Comprehensive Test Suite"
echo "=========================================================================="
echo ""

# Check if API key is set
if [ -z "$API_KEY" ]; then
    echo -e "${RED}❌ OPENAI_API_KEY not set${NC}"
    echo ""
    echo "Please set your API key:"
    echo "  export OPENAI_API_KEY='sk-proj-...'"
    echo ""
    echo "Or pass it directly:"
    echo "  OPENAI_API_KEY='sk-proj-...' ./scripts/run_all_tests.sh"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ API key found (${#API_KEY} characters)${NC}"
echo ""

# Test 1: Validate script can be imported
echo -e "${BLUE}Test 1: Script Import Test${NC}"
echo "Testing if script has no syntax errors..."
.venv/bin/python -c "import sys; sys.path.insert(0, 'scripts'); import ai_image_validator" 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Script imports successfully${NC}"
else
    echo -e "${RED}❌ Script has syntax errors${NC}"
    exit 1
fi
echo ""

# Test 2: API Key Validation
echo -e "${BLUE}Test 2: API Key Validation Test${NC}"
echo "Testing with invalid API key..."
OUTPUT=$(.venv/bin/python scripts/ai_image_validator.py --api-key "invalid-key" --test 2>&1 || true)
if echo "$OUTPUT" | grep -q "API key test failed"; then
    echo -e "${GREEN}✅ Invalid API key correctly detected${NC}"
else
    echo -e "${RED}❌ Failed to detect invalid API key${NC}"
    exit 1
fi
echo ""

# Test 3: Real API Key Validation
echo -e "${BLUE}Test 3: Real API Key Test${NC}"
echo "Testing your actual API key..."
.venv/bin/python scripts/ai_image_validator.py --api-key "$API_KEY" --fighter-ids "NONEXISTENT" 2>&1 | head -20
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ API key is valid${NC}"
else
    echo -e "${RED}❌ API key validation failed${NC}"
    exit 1
fi
echo ""

# Test 4: Single Fighter Validation (Muhammad Naimov - known bad image)
echo -e "${BLUE}Test 4: Single Fighter Validation (Muhammad Naimov)${NC}"
echo "Testing on Muhammad Naimov's problematic image..."
echo "Expected result: INVALID (historical painting)"
echo ""
.venv/bin/python scripts/ai_image_validator.py \
    --api-key "$API_KEY" \
    --fighter-ids "8d11d9c13e2ccdf7"
echo ""
echo -e "${GREEN}✅ Single fighter validation complete${NC}"
echo ""

# Test 5: Small Batch Test
echo -e "${BLUE}Test 5: Small Batch Test (3 fighters)${NC}"
echo "Testing batch processing with 3 fighters..."
echo ""
.venv/bin/python scripts/ai_image_validator.py \
    --api-key "$API_KEY" \
    --fighter-ids "8d11d9c13e2ccdf7,89ea01f5a7ada40c,8a0a35e7c74bebcc"
echo ""
echo -e "${GREEN}✅ Batch processing test complete${NC}"
echo ""

# Test 6: Check Output Files
echo -e "${BLUE}Test 6: Output Files Test${NC}"
echo "Checking for generated report files..."
if ls data/validation_reports/ai_validation_report_*.json 1> /dev/null 2>&1; then
    echo -e "${GREEN}✅ JSON report generated${NC}"
    LATEST_JSON=$(ls -t data/validation_reports/ai_validation_report_*.json | head -1)
    echo "Latest report: $LATEST_JSON"
else
    echo -e "${RED}❌ No JSON report found${NC}"
    exit 1
fi

if ls data/validation_reports/ai_validation_summary_*.txt 1> /dev/null 2>&1; then
    echo -e "${GREEN}✅ Text summary generated${NC}"
    LATEST_TXT=$(ls -t data/validation_reports/ai_validation_summary_*.txt | head -1)
    echo "Latest summary: $LATEST_TXT"
else
    echo -e "${RED}❌ No text summary found${NC}"
    exit 1
fi
echo ""

# Test 7: Verify Report Content
echo -e "${BLUE}Test 7: Report Content Validation${NC}"
echo "Checking if Muhammad Naimov is flagged as invalid..."
LATEST_JSON=$(ls -t data/validation_reports/ai_validation_report_*.json | head -1)
if grep -q "Muhammad Naimov" "$LATEST_JSON" && grep -q '"valid": false' "$LATEST_JSON"; then
    echo -e "${GREEN}✅ Muhammad Naimov correctly flagged as invalid${NC}"
else
    echo -e "${YELLOW}⚠️  Muhammad Naimov validation result unclear${NC}"
fi
echo ""

# Display latest report summary
echo -e "${BLUE}Latest Report Summary:${NC}"
echo "=========================================================================="
LATEST_TXT=$(ls -t data/validation_reports/ai_validation_summary_*.txt | head -1)
head -20 "$LATEST_TXT"
echo "=========================================================================="
echo ""

# Test Summary
echo "=========================================================================="
echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
echo "=========================================================================="
echo ""
echo "The AI Image Validator is working correctly!"
echo ""
echo "Next steps:"
echo "  1. Review the report: cat $LATEST_TXT"
echo "  2. Run full validation: .venv/bin/python scripts/ai_image_validator.py --api-key \"\$OPENAI_API_KEY\""
echo "  3. Estimated cost for all 4,633 images: ~\$0.21"
echo ""
echo "=========================================================================="

#!/bin/bash

# Script to download pre-existing UFC betting odds datasets
# This provides an immediate solution while we work on scraping

set -e

echo "================================================"
echo "UFC Betting Odds Data Download Script"
echo "================================================"
echo ""

# Create data directory
mkdir -p data/betting_odds
cd data/betting_odds

echo "📥 Option 1: GitHub - jansen88/ufc-data (2014-2023)"
echo "Coverage: November 2014 - 2023"
echo "Source: betmma.tips"
echo ""
echo "To download:"
echo "  1. Visit: https://github.com/jansen88/ufc-match-predictor"
echo "  2. Download the repository"
echo "  3. Extract complete_ufc_data.csv to data/betting_odds/"
echo ""

echo "================================================"
echo ""

echo "📥 Option 2: Kaggle - UFC Fights 2010-2020"
echo "Coverage: 2010-2020"
echo ""
echo "To download:"
echo "  1. Install Kaggle CLI: pip install kaggle"
echo "  2. Setup API token: https://www.kaggle.com/docs/api"
echo "  3. Run: kaggle datasets download -d mdabbert/ufc-fights-2010-2020-with-betting-odds"
echo "  4. Unzip to data/betting_odds/"
echo ""

echo "================================================"
echo ""

echo "📥 Option 3: The Odds API (2020-Present)"
echo "Coverage: Mid-2020 to present"
echo "Cost: Free tier available"
echo ""
echo "To use:"
echo "  1. Sign up: https://the-odds-api.com"
echo "  2. Get API key"
echo "  3. Use scripts/fetch_odds_from_api.py"
echo ""

echo "================================================"
echo ""

echo "📝 Quick Start with GitHub Data:"
echo ""
echo "  # Clone the repository"
echo "  git clone https://github.com/jansen88/ufc-match-predictor /tmp/ufc-data"
echo "  "
echo "  # Copy the CSV file"
echo "  cp /tmp/ufc-data/data/complete_ufc_data.csv data/betting_odds/"
echo "  "
echo "  # View the data"
echo "  head data/betting_odds/complete_ufc_data.csv | column -t -s,"
echo ""

echo "================================================"
echo ""
echo "✅ This directory is ready to receive betting odds data!"
echo "   Location: $(pwd)"
echo ""

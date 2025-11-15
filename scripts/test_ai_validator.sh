#!/bin/bash
# Quick test script for AI image validator
# Replace YOUR_API_KEY_HERE with your actual OpenAI API key

API_KEY="YOUR_API_KEY_HERE"

if [ "$API_KEY" == "YOUR_API_KEY_HERE" ]; then
    echo "❌ Please edit this file and replace YOUR_API_KEY_HERE with your actual OpenAI API key"
    echo ""
    echo "Get your key at: https://platform.openai.com/api-keys"
    exit 1
fi

echo "Testing AI image validator on Muhammad Naimov (known bad image)..."
echo ""

.venv/bin/python scripts/ai_image_validator.py \
    --api-key "$API_KEY" \
    --fighter-ids "8d11d9c13e2ccdf7"

#!/usr/bin/env python3
"""Simple API key test to diagnose issues."""

import os
import sys
import asyncio
from openai import AsyncOpenAI

async def test_key():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        sys.exit(1)

    print(f"✅ API key found")
    print(f"   Length: {len(api_key)} characters")
    print(f"   First 10 chars: {api_key[:10]}")
    print(f"   Last 4 chars: ...{api_key[-4:]}")
    print(f"   Starts with 'sk-': {api_key.startswith('sk-')}")
    print(f"   Starts with 'sk-proj-': {api_key.startswith('sk-proj-')}")
    print()

    print("🔑 Testing API key with OpenAI...")
    client = AsyncOpenAI(api_key=api_key)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test'"}],
            max_tokens=5,
        )
        print("✅ API key is VALID!")
        print(f"   Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ API key test FAILED:")
        print(f"   Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_key())

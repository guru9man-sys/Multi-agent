#!/usr/bin/env python3
"""Phase 2.2: API Connectivity Test
Verifies that the provided API keys are valid and can communicate with the providers.
"""

import os
import requests
from config import config

def test_tavily():
    print(f"Testing Tavily API...")
    if not config.TAVILY_API_KEY or "your_" in config.TAVILY_API_KEY:
        print("  ⚠️ Skipping: No valid API key provided")
        return False
    
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": config.TAVILY_API_KEY,
                "query": "Hello Tavily",
                "search_depth": "basic"
            },
            timeout=10
        )
        if response.status_code == 200:
            print("  ✅ Connection Successful!")
            return True
        else:
            print(f"  ❌ Connection Failed: HTTP {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_openai():
    print(f"Testing OpenAI API...")
    if not config.OPENAI_API_KEY or "your_" in config.OPENAI_API_KEY:
        print("  ⚠️ Skipping: No valid API key provided")
        return False
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            timeout=10
        )
        if response.status_code == 200:
            print("  ✅ Connection Successful!")
            return True
        else:
            print(f"  ❌ Connection Failed: HTTP {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_gemini():
    print(f"Testing Gemini API...")
    if not config.GEMINI_API_KEY or "your_" in config.GEMINI_API_KEY:
        print("  ⚠️ Skipping: No valid API key provided")
        return False
    
    try:
        # Using the models list endpoint to verify key
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={config.GEMINI_API_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("  ✅ Connection Successful!")
            return True
        else:
            print(f"  ❌ Connection Failed: HTTP {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    print('[PHASE 2.2: API Connectivity Test]')
    print('=' * 60)
    print()

    results = {
        "Tavily": test_tavily(),
        "OpenAI": test_openai(),
        "Gemini": test_gemini(),
    }

    print()
    print('Final Connectivity Summary:')
    print('-' * 60)
    for provider, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED/SKIPPED"
        print(f"{provider:15} : {status}")
    
    print()
    if all(results.values()):
        print('🚀 ALL ACTIVE APIs ARE CONNECTED!')
    else:
        print('⚠️ Some APIs are not connected. Please check your keys.')

if __name__ == "__main__":
    main()

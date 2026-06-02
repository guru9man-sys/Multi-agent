#!/usr/bin/env python3
"""
test_local_llm_selection.py - Test Local LLM Client Configuration
Tests the LocalLLMClientFactory and different Local LLM providers.
"""

import sys
import json
from utils.llm_clients import OllamaClient, VLLMClient, LocalLLMClientFactory
from config import config
from utils.logger import logger

print("=" * 70)
print("🧪 Phase 7.4: Local LLM Selection Test")
print("=" * 70)
print()

# Test 1: Check Configuration
print("📋 [TEST 1] Configuration Check")
print("-" * 70)
print(f"LOCAL_LLM_PROVIDER: {config.LOCAL_LLM_PROVIDER}")
print(f"LOCAL_LLM_MODEL: {config.LOCAL_LLM_MODEL}")
print(f"LOCAL_LLM_ENDPOINT: {config.LOCAL_LLM_ENDPOINT}")
print(f"LOCAL_LLM_TIMEOUT: {config.LOCAL_LLM_TIMEOUT}")
print(f"USE_LOCAL_LLM_ROUTING: {config.USE_LOCAL_LLM_ROUTING}")
print()

# Test 2: Factory Pattern Test
print("🏭 [TEST 2] Factory Pattern - Create Client from Config")
print("-" * 70)
try:
    client = LocalLLMClientFactory.create_from_config(config)
    if client:
        print(f"✓ Client created successfully")
        print(f"  Type: {type(client).__name__}")
        print(f"  Model: {client.model}")
        print(f"  Endpoint: {client.endpoint}")
    else:
        print(f"✗ Failed to create client")
except Exception as e:
    print(f"✗ Error: {e}")
    client = None

print()

# Test 3: Availability Check
print("🔍 [TEST 3] Availability Check")
print("-" * 70)
if client:
    try:
        available = client.is_available()
        if available:
            print(f"✓ Local LLM is available!")
        else:
            print(f"⚠️  Local LLM is NOT available")
            print(f"   Ensure your Local LLM service is running:")
            if isinstance(client, OllamaClient):
                print(f"   $ ollama serve")
            elif isinstance(client, VLLMClient):
                print(f"   $ python -m vllm.entrypoints.openai.api_server --model {client.model}")
    except Exception as e:
        print(f"✗ Availability check failed: {e}")
        available = False
else:
    print(f"⚠️  No client available to check")
    available = False

print()

# Test 4: Generate Response
if available:
    print("💬 [TEST 4] Generate Response")
    print("-" * 70)
    test_prompt = "Respond with ONLY a JSON object. What is the capital of France?\nReturn: {\"capital\": \"answer\", \"confidence\": 0.0-1.0}"
    
    try:
        print(f"Prompt: {test_prompt[:60]}...")
        response = client.generate(test_prompt)
        print(f"\n✓ Response generated successfully!")
        print(f"Response length: {len(response)} characters")
        print(f"\nResponse (first 200 chars):\n{response[:200]}")
        
        # Try to parse as JSON
        try:
            parsed = json.loads(response)
            print(f"\n✓ Response is valid JSON")
            print(f"Parsed: {json.dumps(parsed, indent=2)}")
        except json.JSONDecodeError:
            print(f"\n⚠️  Response is not pure JSON (might need cleaning)")
            
    except Exception as e:
        print(f"✗ Error generating response: {e}")

print()

# Test 5: Multiple Providers
print("🔄 [TEST 5] Test Multiple Providers")
print("-" * 70)

providers = [
    {"provider": "ollama", "model": "qwen2.5", "endpoint": "http://localhost:11434"},
    {"provider": "vllm", "model": "meta-llama/Llama-2-7b-hf", "endpoint": "http://localhost:8000"}
]

for prov in providers:
    try:
        test_client = LocalLLMClientFactory.create_client(
            provider=prov["provider"],
            model=prov["model"],
            endpoint=prov["endpoint"]
        )
        if test_client:
            is_avail = test_client.is_available()
            status = "✓ Available" if is_avail else "✗ Not available"
            print(f"{prov['provider'].upper():8} ({prov['model']:30}) {status}")
        else:
            print(f"{prov['provider'].upper():8} - Failed to create client")
    except Exception as e:
        print(f"{prov['provider'].upper():8} - Error: {str(e)[:40]}")

print()

# Test 6: Routing Decision Simulation
print("🚀 [TEST 6] Routing Decision Simulation (Using Local LLM)")
print("-" * 70)
if available and client:
    from router import LocalRouter
    from database import DBManager
    
    try:
        db = DBManager()
        router = LocalRouter(db, llm_client=client)
        
        user_input = "Research the latest breakthroughs in GLP-1 agonists for longevity"
        print(f"User Input: {user_input}")
        print()
        
        routing_decision = router.route(user_input)
        
        print(f"✓ Routing decision made:")
        print(f"  Assigned Agent: {routing_decision.get('assigned_agent')}")
        print(f"  Confidence: {routing_decision.get('confidence'):.2%}")
        print(f"  Reasoning: {routing_decision.get('reasoning')}")
        print(f"  Escalate to Cloud: {routing_decision.get('escalate_to_cloud')}")
        
    except Exception as e:
        print(f"✗ Error in routing simulation: {e}")
        import traceback
        traceback.print_exc()
else:
    print("⚠️  Skipping routing test - Local LLM not available")

print()
print("=" * 70)
print("✅ Test Suite Complete!")
print("=" * 70)

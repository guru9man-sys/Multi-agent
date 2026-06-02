#!/usr/bin/env python3
"""
system_health.py - System Health Dashboard
Provides a comprehensive report on the health of the multi-agent system.
"""

import os
import requests
from config import config
from database import DBManager
from orchestrator_main import AgentOrchestrator

def check_api(name, url, key, method="GET", payload=None):
    """Checks if an API is reachable and the key is valid."""
    if not key or "your_" in key:
        return "⚠️ MISSING KEY"
    
    try:
        if method == "POST":
            # For OpenAI/Tavily etc.
            headers = {"Authorization": f"Bearer {key}"} if "openai" in url else {}
            if "tavily" in url:
                # Tavily expects key in JSON
                payload = payload or {}
                payload["api_key"] = key
                headers = {}
            
            response = requests.post(url, json=payload, headers=headers, timeout=5)
        else:
            # For Gemini etc.
            url_with_key = f"{url}?key={key}" if "?" not in url else f"{url}&key={key}"
            response = requests.get(url_with_key, timeout=5)
            
        if response.status_code == 200:
            return "✅ ONLINE"
        else:
            return f"❌ ERROR {response.status_code}"
    except Exception as e:
        return f"❌ UNREACHABLE ({type(e).__name__})"

def main():
    print("\n" + "="*60)
    print("🚀 MULTI-AGENT SYSTEM HEALTH DASHBOARD")
    print("="*60)
    print()

    # 1. Database Health
    print("--- [1] Database Status ---")
    try:
        db = DBManager()
        print("✅ SQLite Database: Connected")
        # Check if tables exist
        session = db.Session()
        tasks_count = session.query(db.TaskRecord).count()
        session.close()
        print(f"✅ Total Tasks Recorded: {tasks_count}")
    except Exception as e:
        print(f"❌ Database Error: {e}")

    print("\n--- [2] API Connectivity ---")
    # Tavily
    tavily_status = check_api(
        "Tavily", 
        "https://api.tavily.com/search", 
        config.TAVILY_API_KEY, 
        method="POST", 
        payload={"query": "health check"}
    )
    print(f"Tavily Search API : {tavily_status}")

    # OpenAI
    openai_status = check_api(
        "OpenAI", 
        "https://api.openai.com/v1/models", 
        config.OPENAI_API_KEY
    )
    print(f"OpenAI GPT-4o API : {openai_status}")

    # Gemini
    gemini_status = check_api(
        "Gemini", 
        "https://generativelanguage.googleapis.com/v1beta/models", 
        config.GEMINI_API_KEY
    )
    print(f"Gemini Pro API    : {gemini_status}")

    # Qwen Cloud
    qwen_status = check_api(
        "Qwen Cloud", 
        "https://dashscope.aliyuncs.com/api/v1/services/dashscope-llm/generation", 
        config.QWEN_API_KEY, 
        method="POST", 
        payload={"model": "qwen-max", "input": {"prompt": "hi"}}
    )
    print(f"Qwen Cloud API    : {qwen_status}")

    print("\n--- [3] Orchestrator Status ---")
    try:
        orch = AgentOrchestrator(db)
        print("✅ Orchestrator: Initialized")
        print(f"✅ Agents Loaded: {len(orch.architect) if hasattr(orch, 'architect') else 'Unknown'}") # Simplified check
    except Exception as e:
        print(f"❌ Orchestrator Error: {e}")

    print("\n" + "="*60)
    print("Dashboard Check Completed.")
    print("="*60)

if __name__ == "__main__":
    main()

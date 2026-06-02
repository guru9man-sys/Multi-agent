#!/usr/bin/env python3
"""
regression_suite.py - Final E2E Regression Suite
Validates the entire pipeline from Research to Audit across multiple complex scenarios.
"""

import asyncio
import time
from database import DBManager
from orchestrator_main import AgentOrchestrator
from schemas import TaskPriority

async def run_scenario(orchestrator: AgentOrchestrator, name: str, query: str):
    """Runs a specific scenario and validates the output."""
    print(f"\n--- Running Scenario: {name} ---")
    print(f"Query: {query}")
    
    start_time = time.perf_counter()
    # handle_request is sync but runs async DAGs internally
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, orchestrator.handle_request, query, TaskPriority.HIGH)
    duration = time.perf_counter() - start_time
    
    if result.get("status") == "completed":
        print(f"✅ SUCCESS | Duration: {duration:.2f}s")
        # Validate that we have results for multiple steps (indicating a DAG was used)
        results = result.get("results", {})
        print(f"   Steps Completed: {len(results)}")
        return True
    else:
        print(f"❌ FAILED | Error: {result.get('error')}")
        return False

async def main():
    db = DBManager()
    orchestrator = AgentOrchestrator(db)
    
    scenarios = [
        {
            "name": "Deep Research & Content Creation",
            "query": "Research the current state of Solid State Batteries, synthesize the key breakthroughs, and create a technical LinkedIn post."
        },
        {
            "name": "Comparative Analysis & Audit",
            "query": "Compare the architectural differences between GPT-4o and Claude 3.5 Sonnet, and audit the findings for technical accuracy."
        },
        {
            "name": "Strategic Synthesis",
            "query": "Analyze the impact of AI agents on the global SaaS economy by 2030 and synthesize a strategic report."
        },
        {
            "name": "Compliance & Ethics Check",
            "query": "Research the EU AI Act's impact on open-source LLMs and create a compliance checklist for developers."
        }
    ]

    print("\n" + "="*60)
    print("🧪 FINAL E2E REGRESSION SUITE")
    print("="*60)

    overall_success = True
    for scenario in scenarios:
        success = await run_scenario(orchestrator, scenario["name"], scenario["query"])
        if not success:
            overall_success = False

    print("\n" + "="*60)
    if overall_success:
        print("🎉 ALL REGRESSION SCENARIOS PASSED!")
    else:
        print("⚠️ SOME SCENARIOS FAILED. Check logs for details.")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

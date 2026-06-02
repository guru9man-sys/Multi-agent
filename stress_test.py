#!/usr/bin/env python3
"""
stress_test.py - System Stress & Load Analysis
Validates the stability of the multi-agent system under high concurrency.
"""

import asyncio
import time
import uuid
from typing import List
from database import DBManager
from orchestrator_main import AgentOrchestrator
from schemas import TaskPriority

async def run_complex_request(orchestrator: AgentOrchestrator, request_id: int, query: str):
    """Executes a single complex request and tracks performance."""
    start_time = time.perf_counter()
    print(f"[StressTest] Launching Request #{request_id}: {query[:30]}...")
    
    try:
        # handle_request is synchronous but calls asyncio.run internally for DAGs.
        # To avoid nested event loops in a stress test, we use a thread pool or 
        # wrap the orchestrator's logic. Since handle_request uses asyncio.run,
        # we run it in a separate thread to simulate concurrent users.
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, orchestrator.handle_request, query, TaskPriority.HIGH)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        if result.get("status") == "completed":
            print(f"✅ Request #{request_id} COMPLETED in {duration:.2f}s")
            return True, duration
        else:
            print(f"❌ Request #{request_id} FAILED: {result.get('error')}")
            return False, duration
    except Exception as e:
        print(f"💥 Request #{request_id} CRASHED: {e}")
        return False, 0

async def main():
    # Setup
    db = DBManager()
    orchestrator = AgentOrchestrator(db)
    
    # Test Scenarios: A mix of simple and complex queries to trigger DAGs
    queries = [
        "Research the impact of quantum computing on RSA encryption and write a LinkedIn post.",
        "Analyze the current state of fusion energy and compare ITER vs Helion.",
        "Create a comprehensive guide on Thai Traditional Medicine for a global audience.",
        "Audit the ethical implications of AGI in healthcare and suggest safeguards.",
        "Research the latest trends in multi-agent systems and synthesize a report.",
        "Compare the efficiency of GPT-4o vs Gemini 1.5 Pro for long-context retrieval.",
        "Analyze the growth of the AI agent economy in 2026.",
        "Synthesize a strategy for deploying autonomous AI trading bots in volatile markets.",
        "Research the intersection of LLMs and bioinformatics for drug discovery.",
        "Create a technical breakdown of the Hybrid Router architecture used in this system."
    ] * 2  # 20 total requests

    print("\n" + "="*60)
    print("🔥 STARTING SYSTEM STRESS TEST")
    print(f"Total Requests: {len(queries)}")
    print("="*60 + "\n")

    start_test_time = time.perf_counter()
    
    # Launch all requests concurrently
    tasks = [run_complex_request(orchestrator, i+1, q) for i, q in enumerate(queries)]
    results = await asyncio.gather(*tasks)
    
    end_test_time = time.perf_counter()
    total_duration = end_test_time - start_test_time

    # Analysis
    successes = [r for r, d in results if r]
    durations = [d for r, d in results if r]
    
    print("\n" + "="*60)
    print("📊 STRESS TEST RESULTS")
    print("="*60)
    print(f"Total Time:      {total_duration:.2f}s")
    print(f"Success Rate:    {len(successes)}/{len(queries)} ({len(successes)/len(queries):.1%})")
    if durations:
        print(f"Avg Latency:     {sum(durations)/len(durations):.2f}s")
        print(f"Max Latency:     {max(durations):.2f}s")
        print(f"Min Latency:     {min(durations):.2f}s")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

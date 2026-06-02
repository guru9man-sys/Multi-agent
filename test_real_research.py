#!/usr/bin/env python3
"""Phase 3.1: Test Real Research Execution
Verifies that KnowledgeArchitect can perform real web searches using Tavily API.
"""

import os
from database import DBManager
from orchestrator_main import AgentOrchestrator
from schemas import TaskRequest, TaskPriority, AgentRole, TaskAction

print('[PHASE 3.1: Real Research Test]')
print('=' * 60)
print()

# Initialize system
try:
    db = DBManager()
    orch = AgentOrchestrator(db)
    print('[OK] System initialized')
except Exception as e:
    print(f'[ERROR] Initialization: {e}')
    exit(1)

# Test Case: Real-world query
user_query = "Latest breakthroughs in longevity and anti-aging research 2026"

try:
    print(f"Executing Real Research for: '{user_query}'")
    print('-' * 60)
    
    # Create a direct request to Knowledge Architect
    request = TaskRequest(
        task_id="test_real_research_001",
        agent_role=AgentRole.KNOWLEDGE_ARCHITECT,
        action=TaskAction.RESEARCH,
        payload={"instruction": user_query}
    )
    
    # Execute agent directly
    response = orch.architect.execute(request)
    
    if response.status == "completed":
        print("\n✅ SUCCESS: Real research completed!")
        print(f"Sources found: {response.meta.get('sources_count', 0)}")
        print("\n--- Primary Output (Knowledge Map) ---")
        print(response.artifacts.get("primary_output"))
        print("\n--- Supporting Data (First 200 chars) ---")
        print(response.artifacts.get("supporting_data")[:200] + "...")
    else:
        print(f"\n❌ FAILURE: Agent returned status {response.status}")
        print(f"Error: {response.error_message}")

except Exception as e:
    print(f"\n❌ Unexpected Error: {e}")
    import traceback
    traceback.print_exc()

print()
print('=' * 60)

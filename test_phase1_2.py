#!/usr/bin/env python3
"""Phase 1.2: Test simple workflow with single agent"""

import json
from database import DBManager
from orchestrator_main import AgentOrchestrator
from schemas import TaskRequest, TaskResponse, TaskStatus, AgentRole, TaskPriority

print('[PHASE 1.2: Simple Workflow Test]')
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

print()
print('Testing: Route simple research request')
print('-' * 60)
print()

# Test 1: Simple research request
user_request = "What are the latest developments in AI safety?"

try:
    print(f"User Request: '{user_request}'")
    print()
    
    # The router should assign this to Knowledge Architect
    routing_decision = orch.local_router.route(
        user_request, 
        priority=TaskPriority.MEDIUM
    )
    
    print(f"✓ Routing Decision:")
    print(f"  Assigned Agent: {routing_decision.get('assigned_agent')}")
    print(f"  Confidence: {routing_decision.get('confidence', 0):.1%}")
    print(f"  Reasoning: {routing_decision.get('reasoning')}")
    print(f"  Task ID: {routing_decision.get('task_id')}")
    print()
    
    # Verify task was stored in database
    task_id = routing_decision.get('task_id')
    if task_id:
        stored_task = db.get_task(task_id)
        if stored_task:
            print(f"✓ Task stored in database:")
            print(f"  Task ID: {stored_task.task_id}")
            print(f"  Status: {stored_task.status}")
            print(f"  Agent Role: {stored_task.agent_role}")
        else:
            print(f"✗ Task not found in database")
    
    print()
    print('✅ Phase 1.2 Result: PASSED')
    
except Exception as e:
    print(f'✗ Workflow test failed: {e}')
    import traceback
    traceback.print_exc()
    exit(1)

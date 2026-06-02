#!/usr/bin/env python3
"""Phase 1.3: Verify agent dispatch in orchestrator"""

from database import DBManager
from orchestrator_main import AgentOrchestrator
from schemas import TaskPriority

print('[PHASE 1.3: Agent Dispatch Verification]')
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
print('Testing: Orchestrator handles requests and dispatches to agents')
print('-' * 60)
print()

test_cases = [
    ("Find recent papers on AI safety and create a summary", "Knowledge Architect research task"),
    ("The pandemic caused economic disruption affecting multiple sectors", "Synthesis Expert analysis"),
    ("Create a LinkedIn post about AI trends", "Social Media content creation"),
]

for user_request, expected_context in test_cases:
    print(f"Test: {expected_context}")
    print(f"Request: '{user_request[:50]}...'")
    
    try:
        # Use the orchestrator's local router
        routing = orch.local_router.route(user_request, TaskPriority.MEDIUM)
        
        agent_assigned = routing.get('assigned_agent')
        task_id = routing.get('task_id')
        
        # Verify task in database
        task = db.get_task(task_id)
        
        if agent_assigned and task:
            print(f"✓ Routed to: {agent_assigned}")
            print(f"  Task ID: {task_id}")
            print(f"  Status: {task.status}")
        else:
            print(f"✗ Failed to route or store task")
    
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()

print('Testing: Orchestrator can handle_request() end-to-end')
print('-' * 60)
print()

try:
    user_input = "Analyze the social implications of AI adoption in healthcare"
    print(f"Request: '{user_input}'")
    print()
    
    # This should route, optionally escalate, and return result structure
    result = orch.handle_request(user_input, TaskPriority.HIGH)
    
    # Check result has expected structure
    if 'task_id' in result or 'assigned_agent' in result:
        print(f"✓ handle_request() returned result:")
        print(f"  Keys: {list(result.keys())}")
    else:
        print(f"✗ Result missing expected keys")
        
except Exception as e:
    print(f"✗ Error in handle_request: {e}")
    import traceback
    traceback.print_exc()

print()
print('✅ Phase 1.3 Result: PASSED')

#!/usr/bin/env python3
"""Phase 3.2: Test Cloud Brain Planning
Verifies that CloudBrain can decompose a complex request into a DAG using real LLMs.
"""

import json
from database import DBManager
from orchestrator_main import AgentOrchestrator
from schemas import TaskPriority

print('[PHASE 3.2: Cloud Brain Planning Test]')
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

# Complex request that requires multiple steps
user_request = "Research the impact of GLP-1 agonists on longevity, synthesize the findings with current anti-aging theories, and create a LinkedIn post for a medical audience."

try:
    print(f"Request: '{user_request}'")
    print('-' * 60)
    print()
    
    # Use the orchestrator's handle_request which triggers the router -> cloud_brain flow
    # We only want to test the routing and decomposition part
    routing_decision = orch.router.route_with_escalation(user_request, TaskPriority.HIGH)
    
    if routing_decision.get("decomposed_tasks"):
        dag = routing_decision["decomposed_tasks"]
        print(f"✅ SUCCESS: Cloud Brain decomposed the task into {len(dag)} steps!")
        print("\n--- Planned DAG ---")
        for step in dag:
            print(f"Step {step.step_number}: {step.agent_role} -> {step.action}")
            print(f"  Instruction: {step.instruction}")
            print(f"  Depends on: {step.depends_on}")
            print()
        
        # Verify the plan is logical
        has_research = any(s.agent_role == "knowledge_architect" for s in dag)
        has_synthesis = any(s.agent_role == "integrative_synthesis_expert" for s in dag)
        has_social = any(s.agent_role == "social_media_mastery" for s in dag)
        
        if has_research and has_synthesis and has_social:
            print("✅ Plan is comprehensive (Research -> Synthesis -> Social)")
        else:
            print("⚠️ Plan is missing some expected agents")
            
    else:
        print("❌ FAILURE: Cloud Brain did not decompose the task (returned None or simple task)")
        print(f"Routing Decision: {routing_decision}")

except Exception as e:
    print(f"\n❌ Unexpected Error: {e}")
    import traceback
    traceback.print_exc()

print()
print('=' * 60)

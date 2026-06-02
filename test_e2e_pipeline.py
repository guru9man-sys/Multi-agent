#!/usr/bin/env python3
"""Phase 4: End-to-End (E2E) Execution Test
Tests the full pipeline from user request to final audited output.
"""

import json
from database import DBManager
from orchestrator_main import AgentOrchestrator
from schemas import TaskPriority

print('[PHASE 4: END-TO-END EXECUTION TEST]')
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

# Complex request that triggers the full pipeline:
# Research -> Synthesis -> Content Creation -> QA Audit
user_request = "Research the latest breakthroughs in GLP-1 agonists for longevity, synthesize the findings, and create a professional LinkedIn post for medical doctors. Please ensure the final output is audited for medical accuracy."

try:
    print(f"🚀 Starting E2E Pipeline for request:")
    print(f"'{user_request}'")
    print('-' * 60)
    print()
    
    # Execute the full pipeline via orchestrator
    result = orch.handle_request(user_request, TaskPriority.HIGH)
    
    print()
    print('=' * 60)
    print('🏁 FINAL PIPELINE RESULT')
    print('=' * 60)
    
    if result and 'results' in result:
        print(f"Status: {result.get('status')}")
        print(f"Total Steps Executed: {result.get('total_steps')}")
        print(f"Completed Steps: {result.get('completed_steps')}")
        
        print("\n--- Final Artifacts ---")
        for step, data in result['results'].items():
            print(f"\n[{step}] Output:")
            # Print a snippet of the output
            content = str(data)
            print(content[:500] + "..." if len(content) > 500 else content)
            
        print("\n✅ E2E Pipeline executed successfully!")
    else:
        print("❌ Pipeline failed to produce results.")
        print(f"Result: {result}")

except Exception as e:
    print(f"\n❌ Critical Pipeline Error: {e}")
    import traceback
    traceback.print_exc()

print()
print('=' * 60)

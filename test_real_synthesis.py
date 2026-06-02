#!/usr/bin/env python3
"""Phase 3.3: Test Real Synthesis Execution
Verifies that SynthesisExpert can analyze real artifacts using LLMs.
"""

import os
from database import DBManager, ArtifactRecord
from orchestrator_main import AgentOrchestrator
from schemas import TaskRequest, TaskStatus, AgentRole, TaskAction

print('[PHASE 3.3: Real Synthesis Test]')
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

# Setup: Create a mock research artifact to synthesize
parent_id = "test_parent_001"
sub_task_id = "test_sub_001"

# Manually insert a research artifact into DB
try:
    # We need to create the task first because of foreign key
    from database import TaskRecord
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Use the same DB path as DBManager
    db_path = "c:\\Users\\EkkaluckPC\\Documents\\LLM wiki\\agents_system\\agent_system.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create parent task
    parent_task = TaskRecord(task_id=parent_id, status="completed", agent_role="orchestrator")
    session.merge(parent_task)
    
    # Create sub task
    sub_task = TaskRecord(task_id=sub_task_id, parent_task_id=parent_id, status="completed", agent_role="knowledge_architect")
    session.merge(sub_task)
    
    # Create artifact
    artifact = ArtifactRecord(
        task_id=sub_task_id,
        content={
            "primary_output": "Longevity research shows that GLP-1 agonists may reduce inflammation.",
            "supporting_data": "Source A: GLP-1 reduces systemic inflammation. Source B: GLP-1 may increase muscle mass loss."
        }
    )
    session.merge(artifact)
    session.commit()
    session.close()
    print("[OK] Mock research artifacts created in database")
except Exception as e:
    print(f"[ERROR] Setup failed: {e}")
    exit(1)

try:
    print(f"\nExecuting Synthesis for Parent ID: {parent_id}")
    print('-' * 60)
    
    # Create synthesis request
    request = TaskRequest(
        task_id="test_synthesis_001",
        agent_role=AgentRole.SYNTHESIS_EXPERT,
        action=TaskAction.ANALYZE,
        payload={"parent_id": parent_id}
    )
    
    # Execute agent directly
    response = orch.synthesis_expert.execute(request)
    
    if response.status == TaskStatus.COMPLETED:
        print("\n✅ SUCCESS: Real synthesis completed!")
        print("\n--- Final Synthesis Report ---")
        print(response.artifacts.get("primary_output"))
        print("\n--- Contradictions ---")
        print(response.artifacts.get("contradictions"))
        print("\n--- Systemic Links ---")
        print(response.artifacts.get("systemic_links"))
    else:
        print(f"\n❌ FAILURE: Agent returned status {response.status}")
        print(f"Error: {response.error_message}")

except Exception as e:
    print(f"\n❌ Unexpected Error: {e}")
    import traceback
    traceback.print_exc()

print()
print('=' * 60)

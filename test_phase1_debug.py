#!/usr/bin/env python3
"""Phase 1.1: Debug initialization test"""

import traceback
from database import DBManager

print('[PHASE 1: Integration Testing - Debug]')
print('=' * 60)
print()

try:
    db = DBManager()
    print('[OK] Database initialized')
except Exception as e:
    print(f'[ERROR] Database: {e}')
    traceback.print_exc()
    exit(1)

try:
    from orchestrator_main import AgentOrchestrator
    print('[OK] Imports successful')
except Exception as e:
    print(f'[ERROR] Import failed:')
    traceback.print_exc()
    exit(1)

try:
    orch = AgentOrchestrator(db)
    print('[OK] Orchestrator initialized')
except Exception as e:
    print(f'[ERROR] Orchestrator initialization failed:')
    traceback.print_exc()
    exit(1)

# Verify all agents
agents = {
    'Knowledge Architect': orch.architect,
    'Synthesis Expert': orch.synthesis_expert,
    'Social Mastery': orch.social_mastery,
    'SRE Agent': orch.sre,
    'QA Auditor': orch.qa_auditor,
}

print()
print('Verifying all agents:')
print('-' * 60)

all_ok = True
for name, agent in agents.items():
    status = '[OK]' if agent else '[FAIL]'
    class_name = agent.__class__.__name__ if agent else 'None'
    print(f'{status} {name:20} -> {class_name}')
    if not agent:
        all_ok = False

print()
if all_ok:
    print('✅ SUCCESS: All 6 agents initialized and ready!')
    print()
    print('Phase 1.1 Result: PASSED ✅')
else:
    print('❌ FAILURE: Some agents failed to initialize')
    exit(1)

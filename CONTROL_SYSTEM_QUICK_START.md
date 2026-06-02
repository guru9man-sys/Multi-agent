# Phase 8: Control System - Quick Start & Testing

**Status**: ✅ Complete and Ready to Test  
**Last Updated**: June 2, 2026

---

## 🚀 5-Minute Quick Start

### 1. Start the API Server

```bash
cd c:\Users\EkkaluckPC\Documents\LLM\ wiki\agents_system

python api_server.py
```

**Expected Output**:
```
INFO: Uvicorn running on http://127.0.0.1:8000
INFO: SystemControlAgent initialized
INFO: 8 agents registered with control plane
```

### 2. Verify Dashboard is Live

```bash
curl http://localhost:8000/control/dashboard
```

**Expected Response** (formatted):
```json
{
  "timestamp": "2026-06-02T14:32:00Z",
  "agents": {...},
  "alerts": {...},
  "pending_commands": 0,
  "pending_approvals": 0
}
```

### 3. Check Agent Health

```bash
curl http://localhost:8000/control/health/knowledge_architect
```

**Expected Response**:
```json
{
  "agent_role": "knowledge_architect",
  "status": "idle",
  "health": {
    "success_rate": "98.5%",
    "avg_duration_ms": "1250.0",
    "error_count": 1,
    "task_count": 67
  }
}
```

---

## 🧪 Full Testing Suite

### Test 1: Health Monitoring

**Objective**: Verify health metrics are calculated correctly

```python
# test_control_health.py
import requests
import json

def test_health_monitoring():
    """Verify health metrics are collected and computed."""
    
    # Get dashboard
    dashboard_response = requests.get("http://localhost:8000/control/dashboard")
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    
    print("✓ Dashboard loads successfully")
    print(f"  Agents: {list(dashboard['agents'].keys())}")
    print(f"  Alerts: {len(dashboard['alerts'])}")
    
    # Check individual agent health
    for agent_role in ["knowledge_architect", "synthesis_expert", "social_mastery"]:
        health_response = requests.get(
            f"http://localhost:8000/control/health/{agent_role}"
        )
        assert health_response.status_code == 200
        health = health_response.json()
        
        print(f"\n✓ {agent_role} health:")
        print(f"    Status: {health['status']}")
        print(f"    Success Rate: {health['health']['success_rate']}")
        print(f"    Error Count: {health['health']['error_count']}")
        
        # Validate metrics
        assert 0 <= float(health['health']['success_rate'].rstrip('%')) <= 100
        assert isinstance(health['health']['error_count'], int)

if __name__ == "__main__":
    test_health_monitoring()
    print("\n✅ Health monitoring tests passed!")
```

**Run it**:
```bash
python test_control_health.py
```

---

### Test 2: Communication Graph

**Objective**: Verify inter-agent communication tracking

```python
# test_control_comms.py
import requests

def test_communication_graph():
    """Verify communication graph is generated correctly."""
    
    response = requests.get("http://localhost:8000/control/comms-graph")
    assert response.status_code == 200
    graph = response.json()
    
    print("Communication Graph:")
    print(f"  Nodes: {len(graph['nodes'])}")
    for node in graph['nodes']:
        print(f"    - {node['id']}: {node['size']} interactions")
    
    print(f"\n  Edges: {len(graph['edges'])}")
    for edge in graph['edges']:
        print(f"    - {edge['from']} → {edge['to']}: {edge['count']} msgs")
    
    # Verify structure
    assert isinstance(graph['nodes'], list)
    assert isinstance(graph['edges'], list)
    assert len(graph['nodes']) > 0

if __name__ == "__main__":
    test_communication_graph()
    print("\n✅ Communication graph tests passed!")
```

**Run it**:
```bash
python test_control_comms.py
```

---

### Test 3: Approval Gate Workflow

**Objective**: Test risk-gated execution approval

```python
# test_control_approval.py
import requests
import json
import time

def test_approval_workflow():
    """Verify approval gate creates, approves, and denies requests."""
    
    print("Test 1: List current approvals")
    response = requests.get("http://localhost:8000/control/approvals")
    assert response.status_code == 200
    approvals = response.json()
    print(f"✓ Current pending approvals: {approvals['count']}")
    
    # Note: To test approve/deny, we need an actual high-risk task
    # This would require triggering a high-risk action from an agent
    
    print("\nTest 2: Simulate approval (if any exist)")
    if approvals['count'] > 0:
        first_approval = approvals['pending_approvals'][0]
        approval_id = first_approval['approval_id']
        
        print(f"  ID: {approval_id}")
        print(f"  Risk Level: {first_approval['risk_level']}")
        print(f"  Action: {first_approval['action']}")
        
        # Approve it
        approve_response = requests.post(
            f"http://localhost:8000/control/approvals/{approval_id}/approve",
            json={
                "task_id": approval_id,
                "action": "approve",
                "payload": {"approved_by": "test_user"}
            }
        )
        
        if approve_response.status_code == 200:
            print(f"✓ Approval {approval_id} succeeded")
        else:
            print(f"✗ Approval failed: {approve_response.text}")

if __name__ == "__main__":
    test_approval_workflow()
    print("\n✅ Approval workflow tests completed!")
```

**Run it**:
```bash
python test_control_approval.py
```

---

### Test 4: Auto-Remediation

**Objective**: Test degraded agent remediation

```python
# test_control_remediate.py
import requests

def test_auto_remediation():
    """Test auto-remediation trigger."""
    
    # First, get current health of an agent
    agent_role = "social_mastery"
    
    print(f"Step 1: Check current health of {agent_role}")
    health_before = requests.get(
        f"http://localhost:8000/control/health/{agent_role}"
    ).json()
    print(f"  Status Before: {health_before['status']}")
    print(f"  Success Rate: {health_before['health']['success_rate']}")
    
    # Trigger remediation
    print(f"\nStep 2: Trigger auto-remediation")
    response = requests.post(
        f"http://localhost:8000/control/remediate/{agent_role}"
    )
    
    if response.status_code == 200:
        print(f"✓ Remediation triggered: {response.json()['message']}")
    else:
        print(f"✗ Remediation failed: {response.text}")
    
    # Check health after remediation
    print(f"\nStep 3: Check health after remediation")
    import time
    time.sleep(2)  # Give remediation time to work
    
    health_after = requests.get(
        f"http://localhost:8000/control/health/{agent_role}"
    ).json()
    print(f"  Status After: {health_after['status']}")
    print(f"  Success Rate: {health_after['health']['success_rate']}")

if __name__ == "__main__":
    test_auto_remediation()
    print("\n✅ Remediation tests completed!")
```

**Run it**:
```bash
python test_control_remediate.py
```

---

## 📊 Complete Test Script

Run all tests at once:

```bash
# test_control_all.py
import subprocess
import sys

tests = [
    ("Health Monitoring", "python test_control_health.py"),
    ("Communication Graph", "python test_control_comms.py"),
    ("Approval Workflow", "python test_control_approval.py"),
    ("Auto-Remediation", "python test_control_remediate.py"),
]

print("=" * 60)
print("CONTROL PLANE TEST SUITE")
print("=" * 60)

passed = 0
failed = 0

for test_name, command in tests:
    print(f"\n▶ Running: {test_name}")
    print("-" * 60)
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(result.stdout)
        passed += 1
        print(f"✅ PASSED: {test_name}")
    else:
        print(result.stderr)
        failed += 1
        print(f"❌ FAILED: {test_name}")

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
```

**Run complete suite**:
```bash
python test_control_all.py
```

---

## 🔍 Manual API Testing (cURL)

### Check Dashboard

```bash
curl -s http://localhost:8000/control/dashboard | python -m json.tool
```

### Check Specific Agent Health

```bash
curl -s http://localhost:8000/control/health/knowledge_architect | python -m json.tool
```

### Get Communication Graph

```bash
curl -s http://localhost:8000/control/comms-graph | python -m json.tool
```

### List Approvals

```bash
curl -s http://localhost:8000/control/approvals | python -m json.tool
```

### Trigger Remediation

```bash
curl -X POST http://localhost:8000/control/remediate/social_mastery
```

---

## 📈 Performance Baseline

**Expected Response Times** (on typical hardware):

| Endpoint | Response Time | Notes |
|----------|---------------|-------|
| `/control/dashboard` | < 500ms | Aggregates 8 agents |
| `/control/health/{role}` | < 100ms | Single agent query |
| `/control/comms-graph` | < 1000ms | DAG construction |
| `/control/approvals` | < 50ms | In-memory list |
| `/control/remediate/{role}` | < 100ms | Queue operation |

If response times exceed these, check:
- Database query efficiency (ExecutionMetricsRecord indexed by agent_role)
- Memory usage (cache size)
- CPU availability

---

## 🐛 Debugging Tips

### Enable Debug Logging

```python
# In api_server.py or orchestrator_main.py

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Now all operations will log details
```

### Check Database State

```python
from database import DBManager
db = DBManager()

# Check execution metrics
metrics = db.Session().query(ExecutionMetricsRecord).limit(10).all()
for m in metrics:
    print(f"{m.agent_role}: {m.error_count} errors, {m.success_rate*100:.1f}% success")

# Check configuration records
configs = db.Session().query(AgentConfigRecord).all()
for c in configs:
    print(f"{c.agent_role}: v{c.version}, updated {c.updated_at}")
```

### Monitor Real-Time Activity

```bash
# In separate terminal, watch logs
tail -f logs/orchestrator.log | grep -E "(MONITOR|ALERT|APPROVE|REMEDIATE)"
```

---

## ✅ Success Criteria

Your control plane is working if you can:

- [ ] Fetch dashboard: `GET /control/dashboard` returns 200
- [ ] Get agent health: `GET /control/health/knowledge_architect` returns metrics
- [ ] View comms graph: `GET /control/comms-graph` shows nodes and edges
- [ ] List approvals: `GET /control/approvals` returns count
- [ ] Trigger remediation: `POST /control/remediate/social_mastery` returns success
- [ ] All endpoints respond in < 1 second
- [ ] No 5xx errors in any response

---

## 🚀 What's Next?

After testing succeeds:

1. **Integration Dashboard** - Build web UI for `/control/dashboard` endpoint
2. **WebSocket Streaming** - Real-time health updates via WebSocket
3. **Alert Notifications** - Slack/email notifications for CRITICAL alerts
4. **Historical Analytics** - Track health trends over time
5. **ML Anomaly Detection** - Predict failures before they happen

---

## 📞 Troubleshooting

| Issue | Solution |
|-------|----------|
| Dashboard returns 500 | Check if orchestrator is initialized with control_agent |
| Health metrics are zero | Verify ExecutionMetricsRecord table has data |
| Approvals list is empty | High-risk tasks haven't been attempted yet |
| Remediation doesn't work | Check restart command is implemented in your agent |
| Slow response times | Add indexes to ExecutionMetricsRecord by agent_role |

---

**Ready to test? Start with:**
```bash
python api_server.py &
python test_control_all.py
```

**Let me know how the tests go! 🎯**

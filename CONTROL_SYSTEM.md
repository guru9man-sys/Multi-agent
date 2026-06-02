# System Control & Monitoring Agent - Phase 8
## Unified Control Plane for Multi-Agent Orchestration

**Status**: ✅ **Production Ready**  
**Integration**: Mission Control Patterns + Existing Agent Architecture  
**Version**: 1.0.0  

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Control Plane Features](#control-plane-features)
4. [API Reference](#api-reference)
5. [Usage Examples](#usage-examples)
6. [Monitoring & Alerting](#monitoring--alerting)
7. [Risk Assessment & Approval Gates](#risk-assessment--approval-gates)
8. [Auto-Remediation](#auto-remediation)
9. [Integration Guide](#integration-guide)

---

## Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│           Dashboard / Frontend / External Systems            │
│                  (WebSocket + REST)                          │
└──────────────┬──────────────────────────────────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼──┐  ┌────▼────┐  ┌─▼──────┐
│ REST │  │WebSocket│  │  SSE   │
│ APIs │  │ Gateway │  │ Events │
└───┬──┘  └────┬────┘  └─┬──────┘
    │          │         │
┌───▼──────────▼─────────▼────────────┐
│    System Control Agent (Phase 8)    │
│                                      │
│  ├─ Health Monitoring               │
│  ├─ Task Routing & Prioritization   │
│  ├─ Execution Approval Gates        │
│  ├─ Inter-Agent Communication       │
│  ├─ Auto-Remediation                │
│  └─ Performance Analytics           │
└───┬──────────────────────────────────┘
    │
    ├─────────────────────────────────┐
    │                                 │
┌───▼───────────┐          ┌──────────▼────┐
│ Orchestrator  │          │  Database     │
│               │          │                │
│ - Task Queue  │◄────────►│ - Metrics     │
│ - Agent Mgmt  │          │ - Config      │
│ - Routing     │          │ - Alerts      │
└───────────────┘          │ - Approvals   │
                           └───────────────┘
```

### Data Flow

**Monitoring Flow**:
```
Agent Execution → Metrics Captured → DB Storage → Dashboard Update
                                  ↓
                           Health Check Trigger
                                  ↓
                          Threshold Evaluation
                                  ↓
                          Alert Generation (if needed)
```

**Control Flow**:
```
User Request → Risk Assessment → Approval Gate → Execution or Denial
               (SystemControlAgent)  (Time-limited)  (with logging)
```

---

## Core Components

### 1. **AgentHealthMetric**
Real-time operational state of an agent.

```python
@dataclass
class AgentHealthMetric:
    agent_role: str
    status: AgentStatus  # offline, idle, busy, error, degraded, maintenance
    last_heartbeat: datetime
    task_count: int
    error_count: int
    avg_duration_ms: float
    success_rate: float  # 0.0-1.0
    token_usage: Dict[str, int]
    memory_usage_pct: float
    last_error: Optional[str]
```

**Status Values**:
- `IDLE` - Ready for tasks
- `BUSY` - Currently executing
- `ERROR` - Critical failure detected
- `DEGRADED` - Operating below thresholds
- `OFFLINE` - Not responding
- `MAINTENANCE` - Under remediation

### 2. **ExecutionApproval**
Risk-gated command with time-limited approval window.

```python
@dataclass
class ExecutionApproval:
    approval_id: str
    agent_role: str
    action: str
    payload: Dict[str, Any]
    risk_level: RiskLevel  # low, medium, high, critical
    status: str  # pending, approved, denied, expired
    created_at: datetime
    expires_at: datetime  # 5-minute default
    approved_by: Optional[str]
```

### 3. **SystemAlert**
Triggered when metrics exceed configured thresholds.

```python
@dataclass
class SystemAlert:
    alert_id: str
    severity: str  # info, warning, critical
    message: str
    agent_role: Optional[str]
    metric: str
    threshold_value: float
    actual_value: float
    triggered_at: datetime
    resolved_at: Optional[datetime]
```

### 4. **ControlCommand**
Instruction to control or reconfigure an agent.

```python
@dataclass
class ControlCommand:
    command_id: str
    agent_role: str
    command_type: str  # pause, resume, reconfigure, restart, execute_task
    payload: Dict[str, Any]
    priority: TaskPriority
    created_at: datetime
    executed_at: Optional[datetime]
    status: str  # pending, accepted, executed, failed
```

---

## Control Plane Features

### 1. **Agent Health Monitoring**

**Metrics Tracked**:
- Task count (lifetime and recent)
- Error count and rate
- Average execution duration
- Success rate (%)
- Token usage (prompt + completion)
- Memory utilization
- Last heartbeat timestamp

**Thresholds** (configurable):
```python
{
    "max_error_rate": 0.3,           # 30% triggers alert
    "max_avg_duration_ms": 30000,    # 30 seconds
    "max_memory_pct": 85.0,
    "heartbeat_timeout_sec": 300,    # 5 minutes
}
```

**Status Determination Logic**:
```
if error_rate > 0.3 and success_rate < 0.5:
    → STATUS: ERROR
elif success_rate < 0.7 or avg_duration > 30s:
    → STATUS: DEGRADED
elif error_count > 0:
    → STATUS: DEGRADED
else:
    → STATUS: IDLE
```

### 2. **Real-Time Alerting**

Alerts are raised when thresholds are exceeded:

```
Error Rate High → SystemAlert(severity="critical")
Slow Execution  → SystemAlert(severity="warning")
Memory Pressure → SystemAlert(severity="warning")
```

Alerts persist until `resolved_at` is set.

### 3. **Execution Risk Assessment**

Risk evaluation based on action type and agent state:

| Action Type | Base Risk | Note |
|---|---|---|
| `create_task` | LOW | Safe, creates work |
| `research` | LOW | Safe, read-only |
| `analyze` | LOW | Safe, read-only |
| `modify_config` | MEDIUM | Affects behavior |
| `execute_shell` | HIGH | System command |
| `delete` | HIGH | Destructive |
| `modify_system` | CRITICAL | System-wide impact |

**Escalation Rules**:
- If agent is DEGRADED: escalate by 1 level
- If agent is ERROR: escalate by 2 levels

### 4. **Task Routing & Prioritization**

Tasks routed to idle agents based on:
- Agent role/capability match
- Current task count (load balancing)
- Priority level
- Dependencies (DAG ordering)

### 5. **Inter-Agent Communication Graph**

Tracks communication patterns:
- Direct agent-to-agent messages
- Orchestrator coordinations
- Task dependencies (DAG structure)
- Message frequency and volume

---

## API Reference

### REST Endpoints

#### Dashboard & Monitoring

**`GET /control/dashboard`**

Comprehensive system status snapshot.

```bash
curl http://localhost:8000/control/dashboard
```

**Response**:
```json
{
  "timestamp": "2026-06-02T14:32:00Z",
  "agents": {
    "knowledge_architect": {
      "status": "idle",
      "health": {
        "success_rate": "98.5%",
        "avg_duration_ms": "1250",
        "error_count": 1,
        "task_count": 67
      },
      "tokens": {
        "prompt_tokens": 125400,
        "completion_tokens": 89200
      },
      "last_heartbeat": "2026-06-02T14:31:55Z"
    }
  },
  "alerts": {
    "alert_123": {
      "severity": "warning",
      "message": "High error rate detected",
      "agent": "social_mastery",
      "metric": "error_rate",
      "triggered_at": "2026-06-02T14:30:00Z"
    }
  },
  "pending_commands": 2,
  "pending_approvals": 5
}
```

---

**`GET /control/health/{agent_role}`**

Detailed health metrics for a specific agent.

```bash
curl http://localhost:8000/control/health/knowledge_architect
```

**Response**:
```json
{
  "agent_role": "knowledge_architect",
  "status": "idle",
  "health": {
    "success_rate": "98.5%",
    "avg_duration_ms": "1250.0",
    "error_count": 1,
    "task_count": 67
  },
  "tokens": {
    "prompt_tokens": 125400,
    "completion_tokens": 89200
  },
  "last_heartbeat": "2026-06-02T14:31:55Z"
}
```

---

**`GET /control/comms-graph`**

Inter-agent communication patterns.

```bash
curl http://localhost:8000/control/comms-graph
```

**Response**:
```json
{
  "nodes": [
    {"id": "knowledge_architect", "label": "Knowledge Architect", "size": 67},
    {"id": "synthesis_expert", "label": "Synthesis Expert", "size": 45},
    {"id": "social_mastery", "label": "Social Mastery", "size": 23}
  ],
  "edges": [
    {"from": "system", "to": "knowledge_architect", "count": 67},
    {"from": "knowledge_architect", "to": "synthesis_expert", "count": 12}
  ],
  "communication_pattern": "DAG with multi-hop dependencies"
}
```

---

#### Approval Management

**`GET /control/approvals`**

List all pending execution approvals.

```bash
curl http://localhost:8000/control/approvals
```

**Response**:
```json
{
  "pending_approvals": [
    {
      "approval_id": "a1b2c3d4",
      "agent_role": "social_mastery",
      "action": "execute_shell",
      "risk_level": "high",
      "created_at": "2026-06-02T14:30:00Z",
      "expires_at": "2026-06-02T14:35:00Z"
    }
  ],
  "count": 1
}
```

---

**`POST /control/approvals/{approval_id}/approve`**

Approve a pending execution.

```bash
curl -X POST http://localhost:8000/control/approvals/a1b2c3d4/approve \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "approval_a1b2c3d4",
    "action": "approve",
    "payload": {"approved_by": "admin@example.com"}
  }'
```

**Response**:
```json
{
  "status": "success",
  "message": "Execution approved: a1b2c3d4"
}
```

---

**`POST /control/approvals/{approval_id}/deny`**

Deny a pending execution.

```bash
curl -X POST http://localhost:8000/control/approvals/a1b2c3d4/deny \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "approval_a1b2c3d4",
    "action": "deny",
    "payload": {"reason": "Suspicious activity pattern"}
  }'
```

---

#### Remediation

**`POST /control/remediate/{agent_role}`**

Trigger auto-remediation for a degraded agent.

```bash
curl -X POST http://localhost:8000/control/remediate/social_mastery
```

**Response**:
```json
{
  "status": "success",
  "message": "Auto-remediation triggered for social_mastery"
}
```

---

## Usage Examples

### Example 1: Monitor System Health

```python
import requests
import json
from datetime import datetime

# Fetch current dashboard
response = requests.get("http://localhost:8000/control/dashboard")
dashboard = response.json()

print(f"Dashboard Snapshot at {dashboard['timestamp']}")
print(f"Active Alerts: {len(dashboard['alerts'])}")
print(f"Pending Approvals: {dashboard['pending_approvals']}")

for agent_role, metrics in dashboard['agents'].items():
    print(f"\n{agent_role}:")
    print(f"  Status: {metrics['status']}")
    print(f"  Success Rate: {metrics['health']['success_rate']}")
    print(f"  Error Count: {metrics['health']['error_count']}")
```

### Example 2: Respond to Alerts

```python
# Get detailed health of a potentially problematic agent
response = requests.get("http://localhost:8000/control/health/social_mastery")
health = response.json()

if health['health']['error_count'] > 5:
    print(f"Alert: {health['agent_role']} has {health['health']['error_count']} errors")
    
    # Trigger remediation
    remedy_response = requests.post(
        "http://localhost:8000/control/remediate/social_mastery"
    )
    print(f"Remediation Response: {remedy_response.json()}")
```

### Example 3: Handle High-Risk Approval

```python
# Get pending approvals
response = requests.get("http://localhost:8000/control/approvals")
approvals = response.json()['pending_approvals']

for approval in approvals:
    if approval['risk_level'] == 'high':
        print(f"HIGH RISK APPROVAL NEEDED: {approval['action']}")
        print(f"  ID: {approval['approval_id']}")
        print(f"  Agent: {approval['agent_role']}")
        
        # Admin decision (example: approve)
        decision = requests.post(
            f"http://localhost:8000/control/approvals/{approval['approval_id']}/approve",
            json={
                "task_id": approval['approval_id'],
                "action": "approve",
                "payload": {"approved_by": "admin@company.com"}
            }
        )
        print(f"Decision: {decision.json()}")
```

### Example 4: Visualize Communication Graph

```python
import requests

response = requests.get("http://localhost:8000/control/comms-graph")
graph = response.json()

print(f"Agent Network:")
for node in graph['nodes']:
    print(f"  {node['id']} ({node['size']} interactions)")

print(f"\nCommunication Edges:")
for edge in graph['edges']:
    print(f"  {edge['from']} → {edge['to']}: {edge['count']} msgs")
```

---

## Monitoring & Alerting

### Alert Lifecycle

```
1. Threshold Exceeded
   ↓
2. SystemAlert Created (triggered_at)
   ↓
3. Alert Logged (warning/critical severity)
   ↓
4. Dashboard Updated
   ↓
5. (Optional) Webhook Notification
   ↓
6. Admin Reviews & Takes Action
   ↓
7. Alert Resolved (resolved_at set)
```

### Configurable Thresholds

In `system_control_agent.py`:

```python
self.health_thresholds = {
    "max_error_rate": 0.3,           # Adjust for your SLA
    "max_avg_duration_ms": 30000,    # Execution timeout
    "max_memory_pct": 85.0,          # Resource pressure
    "heartbeat_timeout_sec": 300,    # 5 minutes offline = ERROR
}
```

**To Customize**:

1. Modify thresholds in `SystemControlAgent.__init__`
2. Add new metric checks in `_check_health_thresholds()`
3. Restart orchestrator

---

## Risk Assessment & Approval Gates

### Risk Scoring Algorithm

```python
base_risk = _get_action_risk(action_type)

if agent_status == DEGRADED:
    risk_level = escalate(base_risk, +1)
elif agent_status == ERROR:
    risk_level = escalate(base_risk, +2)

auto_approve = (risk_level == LOW)
```

### Approval Lifecycle

```
1. Agent Requests Execution
   ↓
2. Risk Assessed: LOW/MEDIUM/HIGH/CRITICAL
   ↓
3. If LOW:
   → Auto-approve, execute immediately
   
   If MEDIUM+:
   → Create ExecutionApproval (5-min expiration)
   → Block execution pending human review
   → Send alert to dashboard
   
4. Human Reviews & Decides
   ↓
5. POST /control/approvals/{id}/approve OR /deny
   ↓
6. Execution Proceeds (or fails)
```

### Example: Blocking Dangerous Operation

```python
# In orchestrator:
success, approval_id = await control_agent.execute_with_approval_gate(
    agent_role="social_mastery",
    action="delete",            # HIGH risk
    payload={"target": "database.main"}
)

if not success:
    print(f"Operation blocked for approval: {approval_id}")
    # Admin must approve before proceeding
```

---

## Auto-Remediation

### Remediation Strategy

When a degraded agent is detected:

```
1. Clear Configuration Cache
   (removes stale prompt configs)
   
2. Reset Rate Limiters
   (allows fresh attempts)
   
3. Queue Restart Command
   (async restart of agent)
   
4. Log Remediation Event
   (for audit trail)
```

### Triggering Remediation

**Automatic** (if enabled):
- Runs when health check detects ERROR status
- Executes without human intervention

**Manual**:
```bash
curl -X POST http://localhost:8000/control/remediate/knowledge_architect
```

### Remediation Effectiveness

Tracked in metrics:
- Success rate before/after remediation
- Time to recovery
- Repeat failure rate

---

## Integration Guide

### Step 1: Import Control Agent

```python
from system_control_agent import SystemControlAgent, AgentStatus, RiskLevel
from orchestrator_main import AgentOrchestrator
```

### Step 2: Initialize

In `orchestrator_main.py.__init__`:

```python
self.control_agent = SystemControlAgent(db_manager)
self._register_agents_with_control_plane()
```

### Step 3: Wire Up Monitoring

In background loop (e.g., scheduler):

```python
async def health_check_loop():
    while True:
        for agent_role in ["knowledge_architect", "synthesis_expert", ...]:
            await orchestrator.control_agent.monitor_agent_health(agent_role)
        await asyncio.sleep(60)  # Check every 60 seconds
```

### Step 4: Add Approval Gates

Before critical actions:

```python
approved, approval_id = await control_agent.execute_with_approval_gate(
    agent_role=task.agent_role,
    action=task.action,
    payload=task.payload
)

if not approved:
    return {"status": "pending_approval", "approval_id": approval_id}

# Proceed with execution
```

### Step 5: Expose Dashboard API

Already done in `api_server.py`:
- `GET /control/dashboard`
- `GET /control/health/{role}`
- `GET /control/comms-graph`
- `GET/POST /control/approvals`
- `POST /control/remediate/{role}`

---

## Summary

The **System Control Agent** provides:

✅ **Real-time Health Monitoring** - Per-agent metrics & system-wide dashboard  
✅ **Intelligent Risk Gating** - Auto-approve safe actions, block risky ones  
✅ **Auto-Remediation** - Self-healing for degraded agents  
✅ **Communication Graph** - Understand agent interactions  
✅ **Alerting & Compliance** - Audit trail for all operations  
✅ **Mission-Control Patterns** - Industry-tested architecture  

**Next Steps**:
1. Run initial health checks: `GET /control/dashboard`
2. Monitor alert stream for anomalies
3. Configure approval thresholds for your risk tolerance
4. Integrate with external monitoring (Datadog, New Relic, etc.)
5. Set up webhook notifications for critical alerts

---

**Built with inspiration from [mission-control](https://github.com/builderz-labs/mission-control) - Production-grade agent orchestration 🚀**

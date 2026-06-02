# Mission Control System Analysis

**Repository**: https://github.com/builderz-labs/mission-control

A sophisticated distributed agent control and monitoring platform built on Next.js with SQLite persistence and multi-gateway support.

---

## 1. System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Mission Control UI                       │
│              (Next.js 16 React 19 SPA)                      │
│  31 Panels | Real-time Dashboard | Terminal                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    ┌───▼────┐     ┌────▼────┐    ┌────▼────┐
    │ REST   │     │WebSocket │    │ SSE     │
    │ API    │     │ Gateway  │    │ Events  │
    │ Routes │     │ Protocol │    │ Stream  │
    └───┬────┘     └────┬────┘    └────┬────┘
        │               │               │
┌───────▼───────────────▼───────────────▼──────────┐
│            Core Runtime Engine                    │
│  - Auth & RBAC                                    │
│  - Database Layer (SQLite WAL mode)              │
│  - Event Bus (pub/sub)                            │
│  - Scheduler & Job Queue                         │
│  - Framework Adapters                             │
└───────┬───────────────────────────────────────────┘
        │
    ┌───┴─────────────────────────────────┐
    │                                     │
┌───▼──────────────┐        ┌─────────────▼──────┐
│ OpenClaw Gateway │        │ Local Runtimes     │
│ (WebSocket RPC)  │        │ - Hermes           │
│                  │        │ - Claude Code      │
│ - Sessions       │        │ - OpenCode         │
│ - Agents         │        │ - Codex            │
│ - Tools          │        │ - Generic HTTP     │
└──────────────────┘        └────────────────────┘
```

### Deployment Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16 App Router, React 19, Tailwind CSS 3.4, Zustand 5 |
| **Backend** | Next.js API routes (TypeScript), better-sqlite3 |
| **Database** | SQLite (WAL mode, 45+ migrations) |
| **Realtime** | WebSocket + Server-Sent Events |
| **Auth** | Session tokens, API keys, Google OAuth 2.0, RBAC |
| **Validation** | Zod 4 schemas |
| **Testing** | Vitest + Playwright (165 unit + 295 E2E tests) |

---

## 2. Key Components & Services

### 2.1 Agent Management (`/api/agents`)

**Core Entity: Agent**
```typescript
interface Agent {
  id: number
  name: string
  role: string                    // "researcher", "builder", etc.
  status: 'offline' | 'idle' | 'busy' | 'error'
  session_key?: string            // For direct session targeting
  soul_content?: string           // Agent personality/context
  config?: string                 // JSON configuration
  last_seen?: number              // Unix timestamp
  last_activity?: string          // Last action description
  created_at: number
  updated_at: number
}
```

**Key Endpoints**:
- `GET /api/agents` - List agents with filtering (status, role, limit)
- `POST /api/agents` - Register new agent (template-based or custom)
- `GET /api/agents/[id]` - Agent detail with full config
- `PUT /api/agents/[id]` - Update config (bidirectional gateway write-back)
- `DELETE /api/agents/[id]` - Archive/remove agent
- `GET /api/agents/[id]/heartbeat` - Work item check (mentions, tasks, activities)
- `POST /api/agents/[id]/wake` - Send message to wake sleeping agent
- `GET /api/agents/[id]/diagnostics` - Health check + recent activity
- `GET /api/agents/comms` - Inter-agent communication graph and timeline
- `POST /api/agents/sync` - Sync agents from gateway sessions

**Framework Adapters** (pluggable):
- OpenClaw (native gateway agents)
- LangGraph
- CrewAI
- AutoGen
- Claude SDK
- Generic HTTP (any REST client)

### 2.2 Task Management (`/api/tasks`)

**Task Lifecycle**:
```
backlog → inbox → assigned → in_progress → quality_review → done
                                             (or failed/partial)
```

**Task Schema**:
```typescript
interface Task {
  id: number
  title: string
  description?: string
  status: TaskStatus
  priority: 'low' | 'medium' | 'high' | 'critical' | 'urgent'
  assigned_to?: string            // Agent name
  created_by: string              // User/system
  created_at: number
  updated_at: number
  due_date?: number
  estimated_hours?: number
  actual_hours?: number
  outcome?: 'success' | 'failed' | 'partial' | 'abandoned'
  error_message?: string
  resolution?: string
  feedback_rating?: number        // 1-5
  tags?: string                   // JSON array
  project_id?: number
  project_ticket_no?: number
}
```

**Key Endpoints**:
- `GET /api/tasks` - List with filtering
- `POST /api/tasks` - Create task
- `GET /api/tasks/[id]` - Task detail with comments
- `PUT /api/tasks/[id]` - Update status/fields
- `DELETE /api/tasks/[id]` - Archive
- `GET /api/tasks/queue` - Next assignable tasks
- `GET /api/tasks/outcomes` - Analytics on success/failure rates
- `GET /api/tasks/regression` - Detect quality regressions
- `POST /api/tasks/[id]/comments` - Add comments (with @mentions)

**Task Dispatch**:
- Automatic routing to idle agents by role/capability
- Quality review gates before marking done
- Outcome tracking for continuous improvement

### 2.3 Skills Registry (`/api/skills`)

**Skills** - reusable capabilities installed on agents

```typescript
interface Skill {
  id: number
  name: string
  source: 'disk' | 'registry' | 'github'
  path: string                    // File location
  description?: string
  content_hash: string            // For change detection
  registry_slug?: string          // e.g., "awesome-openclaw/search-web"
  security_status: 'unchecked' | 'safe' | 'flagged'
  installed_at: string
  updated_at: string
}
```

**Capabilities**:
- Security scanning (checks for SSRF, injection, prompt injection)
- Version management
- Registry integration (ClaHub, skills.sh, GitHub)
- Disk-based CRUD

### 2.4 Memory System (`/api/memory`)

**Knowledge Management** with FTS5 index

```typescript
interface MemoryFile {
  path: string                    // Relative in memory dir
  title: string
  content: string
  wikiLinks: WikiLink[]           // [[linked-file]] references
  tags: string[]
  lastModified: number
}
```

**Memory Processing Pipeline** (Ars Contexta-inspired 6 Rs):
- **Reflect**: Find connection opportunities between files
- **Reweave**: Identify stale files needing updates
- **Generate-MOC**: Auto-generate Maps of Content from clusters
- **Gap-Detect**: Find missing documentation
- **Consolidate**: Merge related entries

**Endpoints**:
- `GET /api/memory` - Browse file tree
- `POST /api/memory` - Create/upload file
- `PUT /api/memory/[path]` - Edit file
- `DELETE /api/memory/[path]` - Remove file
- `GET /api/memory/search` - FTS5 search with BM25 ranking
- `POST /api/memory/process` - Run maintenance pass (reflect, reweave, etc.)
- `GET /api/memory/context` - Injection payload for agent session start

### 2.5 Chat & Messaging (`/api/chat`)

**Multi-modal conversation system**

```typescript
interface Message {
  id: number
  conversation_id: string         // "a2a:agent1:agent2" or "session:..."
  from_agent: string              // Sender
  to_agent?: string               // Recipient (null = broadcast)
  content: string
  message_type: 'text' | 'tool_call' | 'result' | 'error'
  metadata?: Record<string, any>  // Tool details, errors, etc.
  read_at?: number
  created_at: number
}
```

**Conversation Patterns**:
- **A2A**: Agent-to-agent direct messaging
- **Coordinator**: Orchestrator → workers
- **Session**: Runtime session threads
- **Broadcast**: System-wide announcements

**Endpoints**:
- `GET /api/chat/messages` - Retrieve thread/feed
- `POST /api/chat/messages` - Send message
- `PATCH /api/chat/messages/[id]` - Mark read
- `GET /api/chat/conversations` - List active conversations
- `PATCH /api/chat/session-prefs` - Rename/color conversations

### 2.6 Security & Execution (`/api/exec-approvals`)

**Execution Control Framework**

```typescript
interface ExecApproval {
  id: string
  sessionId: string
  agentName: string
  toolName: string
  toolArgs: Record<string, any>
  command?: string
  cwd?: string
  risk: 'low' | 'medium' | 'high' | 'critical'
  status: 'pending' | 'approved' | 'denied' | 'expired'
  createdAt: number
  expiresAt?: number
  resolvedAt?: number
  resolvedBy?: string
}
```

**Mechanisms**:
- Per-agent execution allowlists (patterns)
- Risk assessment (SSRF, injection, privilege escalation)
- Real-time approval/denial
- Automatic expiration (5-minute window default)
- Gateway forwarding for approval delivery

**Endpoints**:
- `GET /api/exec-approvals` - Pending requests
- `GET /api/exec-approvals?action=allowlist` - Per-agent patterns
- `PUT /api/exec-approvals` - Update allowlist
- `POST /api/exec-approvals` - Respond to request

### 2.7 Pipelines & Workflows (`/api/pipelines`, `/api/workflows`)

**Pipeline** - sequence of steps with fail handling

```typescript
interface Pipeline {
  id: number
  name: string
  description?: string
  steps: PipelineStep[]           // Sequential tasks
  created_by: string
  use_count: number
}

interface PipelineStep {
  template_id: number
  on_failure: 'stop' | 'continue'
}

interface PipelineRun {
  id: number
  pipeline_id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  current_step: number
  triggered_by: string
  started_at?: number
  completed_at?: number
}
```

**Workflow** - template-based agent task with model + prompt

```typescript
interface Workflow {
  id: number
  name: string
  task_prompt: string             // Task template
  model: string
  timeout_seconds: number
  agent_role?: string
  created_by: string
}
```

### 2.8 Webhooks (`/api/webhooks`)

**Event-driven outbound integration**

```typescript
interface Webhook {
  id: number
  name: string
  url: string
  events: string[]                // ["agent.created", "task.updated", ...]
  enabled: boolean
  retry_count: number
  consecutive_failures: number
  circuit_breaker_status: 'closed' | 'open' | 'half-open'
}

interface WebhookDelivery {
  id: number
  webhook_id: number
  payload: string                 // JSON
  status_code: number
  attempt: number
  next_retry_at?: number
  is_retry: boolean
}
```

**Event Mapping**:
```
Gateway Event → Webhook Event Type → HTTP POST delivery
agent.created → agent.created
task.status_changed → activity.task_status_changed
agent.error → agent.error (special case)
```

**Retry Strategy**:
- Exponential backoff with ±20% jitter
- Circuit breaker after 5+ consecutive failures
- Webhook signature (HMAC-SHA256) for verification

### 2.9 Cron & Scheduling (`/api/cron`, `/api/scheduler`)

**Recurring task automation**

```typescript
interface CronJob {
  id: string
  name: string
  schedule: string                // 5-field cron expression
  task_template?: string
  agent_filter?: string
  status: 'active' | 'paused' | 'failed'
  last_run_at?: number
  next_run_at?: number
  error?: string
}
```

**Scheduler Responsibilities** (`/api/scheduler` - internal tick endpoint):
- Detect stale agents (no heartbeat > threshold)
- Reconcile task assignments
- Route pending tasks to agents
- Dispatch and retry logic
- Data cleanup (retention policy)

---

## 3. Communication Patterns

### 3.1 WebSocket Gateway Protocol

**Connection Handshake**:
```
Client                          Gateway
  │                               │
  ├──────── TCP Connect ────────→ │
  │                               │
  ├─ JSON: connect_challenge ────← │
  │  (nonce for device signing)    │
  │                               │
  ├─ JSON: connect request ──────→ │ (includes Ed25519 signature)
  │  (device_id, scopes, auth)     │
  │                               │
  ├─ connect_response ───────────← │
  │  (confirm handshake)           │
  │                               │
  └─ START HEARTBEAT ────────────→ │ (ping every 30s)
```

**Protocol Frames**:
```typescript
interface GatewayFrame {
  type: 'event' | 'req' | 'res'
  event?: string                  // Event type for broadcasts
  method?: string                 // RPC method
  id?: string                     // Request ID
  payload?: any
  ok?: boolean
  result?: any
  error?: {
    message?: string
    code?: string
    details?: any
  }
  seq?: number                    // Sequence for gap detection
}
```

**Key Event Types** (broadcast):
- `connect.challenge` - Initiate handshake
- `agent.status` - Agent online/offline/error
- `chat.message` - New message in feed
- `tool.stream` - Real-time tool output
- `notification` - System notifications
- `exec.approval` - Execution approval request
- `context.compaction` - Session compression progress
- `model.fallback` - Model switching notification
- `log` - Debug/info logs

**RPC Methods** (request/response):
- `agent.list` - Get all agents
- `sessions.spawn` - Create new session
- `node.list` - List cluster nodes
- Error handling: `isUnknownMethodError()` detects deprecated methods

### 3.2 Server-Sent Events (SSE) `/api/events`

**Fallback real-time channel** when WebSocket unavailable

```typescript
interface ServerEvent {
  type: 'agent.created' | 'task.updated' | 'chat.message' | ...
  data: Record<string, any>
  timestamp: number
}
```

**Advantages over WS**:
- Works through HTTP-only proxies
- Automatic reconnection
- Simpler fallback for old clients
- Uses `readLimiter` for rate control

### 3.3 REST API Patterns

**Discovery Endpoint**: `GET /api/index`
- Catalog of 100+ routes
- Organized by tag (Agents, Tasks, Chat, etc.)
- Auth requirements per route
- Dynamic, cacheable (5-minute CDN cache)

**Standard Response Format**:
```typescript
{
  ok: boolean
  data?: T
  error?: string
  status?: number
  total?: number          // Pagination
  limit?: number
  offset?: number
}
```

**Rate Limiting** (adaptive):
- `readLimiter` - Query operations (generous)
- `mutationLimiter` - Write operations (stricter)
- `agentHeartbeatLimiter` - Agent pings (very strict)
- `heavyLimiter` - Exports/backups (very strict)

**Authentication Methods**:
1. **Session Cookie** (`MC_SESSION`) - UI users
2. **API Key** (`Authorization: Bearer <key>`) - Programmatic
3. **Google OAuth** - Browser login with consent flow

---

## 4. Data Models & Database Schema

### 4.1 SQLite Schema (45 Migrations)

**Primary Tables**:

```sql
-- Users & Auth
users                          -- Local/Google auth users
user_sessions                  -- Session tokens, expiration
access_requests                -- Google OAuth access requests
api_keys                        -- API key storage (hashed)

-- Core Entities
agents                         -- Agent registry
tasks                          -- Task queue/kanban
comments                       -- Task comments with @mention parsing
messages                       -- Chat/inter-agent comms
conversations                  -- Thread grouping (derived from messages)

-- Projects & Organization
projects                       -- Grouping tasks
project_agent_assignments      -- Which agents work on projects
workspaces                      -- Multi-tenant isolation
tenants                        -- Super-admin SaaS support

-- Work Tracking
activities                     -- Event stream (agent updated, task created, etc.)
notifications                 -- User notifications
audit_log                      -- Security/compliance audit trail
quality_reviews                -- Quality gates before task completion

-- Skills & Configuration
skills                         -- Installed agent capabilities
workflow_templates             -- Reusable task templates
workflow_pipelines             -- Multi-step automation
pipeline_runs                  -- Execution history + status

-- Memory & Knowledge
(memory files stored on disk)  -- FTS5 index: memory_fts table

-- Execution & Control
exec_approvals                 -- Pending tool/command approvals
direct_connections             -- Direct CLI connection metadata
spawn_history                  -- Agent spawning audit trail

-- Integration & Monitoring
webhooks                       -- Outbound event webhooks
webhook_deliveries             -- Delivery attempts + retries
github_syncs                   -- GitHub issue sync metadata
token_usage                    -- LLM token tracking + costs
settings                       -- Configuration key/values
alert_rules                    -- Custom alert conditions

-- Runtimes & Sessions
claude_sessions                -- Claude Code project tracking
hermes_sessions                -- Hermes agent sessions
opencode_sessions              -- OpenCode IDE sessions
runs                           -- Agent run traces (provenance)
eval_runs                      -- Evaluation test results
eval_golden_sets               -- Golden dataset for evals

-- Infrastructure
gateways                       -- Connected OpenClaw/Hermes gateways
gateway_health_logs            -- Gateway uptime/latency history
provision_jobs                 -- Tenant provisioning tasks
provision_events               -- Job execution events
```

### 4.2 Workspace Isolation

**Workspace** = tenant-scoped namespace (multi-tenancy)

```sql
-- Every table has workspace_id column
SELECT * FROM tasks WHERE workspace_id = ?
SELECT * FROM agents WHERE workspace_id = ?

-- Default workspace_id = 1 for single-tenant deployments
```

**Benefits**:
- SaaS-ready multi-tenancy
- Data isolation without separate databases
- User can belong to multiple workspaces (via session)

### 4.3 Token Usage Tracking

**Cost Monitoring** per model/session/agent

```typescript
interface TokenUsageRecord {
  id: number
  model: string                   // "gpt-4", "claude-opus", etc.
  session_id: string
  input_tokens: number
  output_tokens: number
  cost_usd: number
  agent_name?: string
  task_id?: number
  created_at: number
}
```

**Cost Calculation**:
```typescript
function calculateTokenCost(model: string, inputTokens: number, outputTokens: number): number {
  const modelConfig = getModelByName(model)
  if (!modelConfig) return 0
  const costPer1kTokens = modelConfig.costPer1k
  return (inputTokens + outputTokens) / 1000 * costPer1kTokens
}
```

### 4.4 Activity Stream

**Immutable event log** for dashboards + audit

```typescript
interface Activity {
  id: number
  type: string                    // "agent_created", "task_updated", etc.
  entity_type: string             // "agent", "task", "skill", etc.
  entity_id: number
  actor: string                   // User/system
  description: string
  data?: Record<string, any>      // JSON context
  workspace_id: number
  created_at: number
}
```

**Examples**:
```
type: "agent_created"
description: "Agent 'researcher' created by admin"
data: { name: "researcher", template: "researcher", role: "query_engine" }

type: "task_updated"
description: "Task #42 status changed from 'assigned' to 'in_progress'"
data: { status_from: "assigned", status_to: "in_progress" }

type: "security_event"
description: "Skill 'backdoor.py' flagged for SSRF"
data: { skill_name: "backdoor.py", issues: [{ rule: "ssrf", severity: "critical" }] }
```

---

## 5. Control Mechanisms

### 5.1 Agent Command API

**Direct Commanding** via REST endpoints

```typescript
// POST /api/agents/[id]/wake
// Wake a sleeping agent with custom message
{
  message: "Please review your assigned tasks"
}

// PUT /api/agents/[id]
// Update agent config (with optional gateway write-back)
{
  role: "junior_builder",
  gateway_config: {
    model: { primary: "claude-opus-4-6", fallbacks: ["sonnet"] },
    tools: { web_search: true, file_edit: false }
  },
  write_to_gateway: true  // Sync to OpenClaw gateway
}

// DELETE /api/agents/[id]
// Archive agent + remove from workspace
```

### 5.2 Task Assignment & Dispatch

**Automatic Routing** (`/api/tasks/queue`)

```typescript
// 1. Query pending tasks
const pendingTasks = db.prepare(`
  SELECT * FROM tasks
  WHERE status IN ('inbox', 'assigned')
    AND workspace_id = ?
  ORDER BY priority DESC, created_at ASC
  LIMIT 50
`).all(workspaceId)

// 2. For each task, find eligible agents
const agents = db.prepare(`
  SELECT * FROM agents
  WHERE status = 'idle'
    AND role IN (?, ?, ...)  -- Roles from task tags
    AND workspace_id = ?
`).all(...taskRoles, workspaceId)

// 3. Round-robin or scored assignment
assignTask(task, selectedAgent)

// 4. Broadcast update via WebSocket + SSE
eventBus.broadcast('task.assigned', { task_id, agent_name, assigned_at })
```

**Quality Gates** (`/api/quality-review`):
```
Task → in_progress → review → quality_review → done
       (agent work) (peer)    (human check)
```

### 5.3 Execution Approval Gate

**Block dangerous tool/command execution**

```
Agent attempts exec → MC intercepts → Check allowlist
                                    → Risk assessment
                                    → Require approval (if risky)
                                    → Timeout 5 min
                                    → Auto-expire if not approved
```

**Risk Factors**:
- SSRF (localhost, private IP ranges)
- SQL injection patterns
- Privilege escalation
- Credential access
- Hidden/encoded commands

**Approval Response Flow**:
```
User: approve/deny → MC API → Gateway RPC → Agent notified → Execution proceeds/blocked
```

### 5.4 Cron Automation

**Scheduled Task Execution** (5-field cron + custom scheduling)

```typescript
// Define cron job
{
  name: "daily-report",
  schedule: "0 9 * * *",          // 9am daily
  task_template: "generate_standup_report",
  agent_filter: "role=analyst",
  status: "active"
}

// Scheduler fires on tick
// 1. Detect if next_run_at <= now
// 2. Find matching agents
// 3. Create task(s)
// 4. Log execution in cron_jobs.state
```

### 5.5 Workflow Execution

**Template-based Multi-Step Automation** (`POST /api/pipelines/run`)

```typescript
{
  pipeline_id: 5,
  triggered_by: "schedule"
}

// Creates pipeline_run with status='pending'
// Scheduler processes each step sequentially:
// 1. Execute step 1 (e.g., data fetch task)
// 2. Check result
// 3. If success → step 2
// 4. If fail → check on_failure (stop | continue)
// 5. Record completion_time
```

---

## 6. Monitoring & Observability

### 6.1 Real-Time Dashboards

**Live Metrics via WebSocket**:
- Agent status grid (online/idle/error/offline)
- Task kanban with live drag-drop
- Chat feed with tool call details
- Activity stream (timestamp, actor, description)
- Cost tracker (token usage + USD)
- Cron job status + logs
- Security alerts + approvals

### 6.2 Activity Feed (`/api/activities`)

**Queryable audit log**

```typescript
// GET /api/activities?type=agent_created&actor=admin&hours=24&limit=100
// Returns paginated activity stream

// Supports filtering by:
// - type (agent_created, task_updated, etc.)
// - actor (username)
// - entity_type (agent, task, skill)
// - entity_id
// - since (unix timestamp)
// - hours (last N hours)
```

### 6.3 Agent Heartbeat (`GET /api/agents/[id]/heartbeat`)

**Work Item Detection**

```typescript
// Returns "HEARTBEAT_OK" or work items:
{
  status: 'WORK_ITEMS_FOUND',
  work_items: [
    {
      type: 'assigned_tasks',
      count: 3,
      items: [ { id: 42, title: "...", priority: "high" }, ...]
    },
    {
      type: 'mentions',
      count: 1,
      items: [ { in_comment: "...", context: "..." }, ...]
    },
    {
      type: 'unread_notifications',
      count: 5
    }
  ]
}
```

### 6.4 Agent Comms Graph (`/api/agents/comms`)

**Inter-agent Communication Analysis**

```typescript
// Returns:
{
  messages: [
    {
      id, conversation_id, from_agent, to_agent,
      content, message_type, metadata, created_at
    }
  ],
  graph: {
    edges: [                        // Communication edges
      { from: "agent1", to: "agent2", message_count: 5, last_message_at }
    ],
    agentStats: [                   // Per-agent traffic
      { agent: "agent1", sent: 8, received: 12 }
    ]
  },
  source: {
    mode: 'gateway' | 'seeded',     // Data source
    seededCount: 10,                // Test messages
    liveCount: 42                   // Real messages
  }
}
```

### 6.5 Security Audit (`/api/audit`)

**Compliance Logging**

```typescript
// GET /api/audit?action=agent_gateway_create&actor=admin&limit=1000

interface AuditEntry {
  id: number
  action: string                   // What was done
  actor: string                    // Who did it
  actor_id: number
  target_type: string              // What was modified (agent, task, skill)
  target_id: number
  detail: Record<string, any>      // Context JSON
  ip_address: string
  user_agent: string
  created_at: number
}
```

**Actions Logged**:
- `agent_created`, `agent_updated`, `agent_deleted`
- `agent_gateway_create`, `agent_config_writeback`
- `task_created`, `task_updated`, `task_completed`
- `skill_installed`, `skill_removed`, `skill_security_scan`
- `exec_approval_*`, `user_login`, `user_created`
- `webhook_triggered`, `backup_created`

### 6.6 Token Usage Analytics (`/api/tokens`)

**Cost Tracking by Model/Agent/Task**

```typescript
// GET /api/tokens?action=stats&timeframe=7d&format=json

{
  usage: [
    {
      id: "...",
      model: "claude-opus-4-6",
      sessionId: "...",
      agentName: "builder",
      timestamp: 1719345600000,
      inputTokens: 2500,
      outputTokens: 1200,
      totalTokens: 3700,
      cost: 0.0486,
      operation: "heartbeat"
    }
  ],
  stats: {
    total_tokens: 125000,
    total_cost_usd: 12.45,
    models: {
      "claude-opus-4-6": { tokens: 75000, cost: 10.50 },
      "gpt-4": { tokens: 50000, cost: 1.95 }
    },
    agents: {
      "builder": { tokens: 80000, cost: 8.00 },
      "researcher": { tokens: 45000, cost: 4.45 }
    }
  }
}
```

### 6.7 Performance Tracing

**Agent Run Traces** (`/api/v1/runs`)

```typescript
interface AgentRun {
  id: string                      // UUID
  agent_id: string
  agent_name: string
  model: string
  provider: string
  status: 'pending' | 'completed' | 'failed'
  outcome?: 'success' | 'failure'
  started_at: string              // ISO
  ended_at?: string
  duration_ms?: number
  steps: Array<{                  // Tool calls, decisions
    type: 'tool_use' | 'decision'
    name: string
    duration_ms: number
    result: any
  }>
  cost_usd?: number
  signature?: string              // Ed25519 signing for provenance
  signed_by?: string              // Signer identity
}
```

---

## 7. Scalability & Multi-Tenancy

### 7.1 Workspace Isolation

**Each workspace is independent**:
```sql
-- Queries automatically filtered by workspace
WHERE workspace_id = ?

-- User session includes workspace_id
-- All API endpoints enforce workspace boundary
```

### 7.2 Concurrent Access Patterns

**SQLite Concurrency** (optimized for MC use case):
```typescript
db.pragma('journal_mode = WAL')     // Write-Ahead Log
db.pragma('synchronous = NORMAL')   // Balanced durability
db.pragma('cache_size = 1000')      // In-memory page cache
db.pragma('busy_timeout = 5000')    // 5s retry before SQLITE_BUSY
db.pragma('foreign_keys = ON')      // Referential integrity
```

**Benefits**:
- Multiple readers + 1 writer
- No lock contention for reads
- Automatic journal rollback on crash
- ~98% single-server throughput of Postgres for reads

### 7.3 Rate Limiting Strategy

**Tiered Limiting**:
```typescript
// 1. Global per-user (sessions)
loginLimiter: 5 attempts per 15min

// 2. Read operations (generous)
readLimiter: 100 req/sec per user

// 3. Write operations (stricter)
mutationLimiter: 20 req/sec per user

// 4. Agent heartbeats (very strict - high volume)
agentHeartbeatLimiter: 2 req/sec per agent

// 5. Heavy operations (backups, exports)
heavyLimiter: 1 req/min per user
```

### 7.4 Gateway Scalability

**Multiple Gateways** (`/api/gateways`):
```typescript
// Register multiple OpenClaw instances
{
  name: "primary",
  host: "gateway-1.example.com",
  port: 18789,
  token: "...",
  is_primary: true,
  status: "healthy"
}

// Automatic failover + load balancing
// Probing checks latency + reachability
// WebSocket client reconnects on primary failure
```

### 7.5 Memory Efficiency

**Session Compression** (for long-running sessions):
```
Gateway broadcasts: context.compaction event
→ MC UI shows progress toast
→ Session JSONL deduplicated
→ Tokens reduced by 30-50%
```

### 7.6 Framework Adapter Pattern

**Pluggable Adapters** reduce coupling:
```typescript
interface FrameworkAdapter {
  register(agent: AgentRegistration): Promise<void>
  heartbeat(payload: HeartbeatPayload): Promise<void>
  reportTask(report: TaskReport): Promise<void>
  getAssignments(agentId: string): Promise<Assignment[]>
  disconnect(agentId: string): Promise<void>
}

// Each broadcasts to eventBus - decouples from storage
```

**Current Adapters** (6 frameworks):
- OpenClaw
- LangGraph
- CrewAI
- AutoGen
- Claude SDK
- Generic HTTP

---

## 8. Security & Compliance

### 8.1 Authentication & Authorization

**RBAC Roles**:
```typescript
'admin'     // Full access + super-admin features
'operator'  // Can create tasks, approve executions, manage agents
'viewer'    // Read-only access to dashboards
```

**Session Management**:
- Hashed session tokens (Argon2 equivalent)
- Expiration enforcement (24-48h default)
- IP address + User-Agent logging
- Automatic cleanup of expired sessions

### 8.2 Injection Prevention

**Injection Guard** (`/lib/injection-guard.ts`):
- SQL injection detection (UNION SELECT, DROP TABLE, etc.)
- Command injection (shell metacharacters, base64 encoded)
- Prompt injection (role manipulation, safety bypass)
- Used as Zod refinement for input validation

**Example**:
```typescript
const taskSchema = z.object({
  title: z.string().refine(
    input => !scanForInjection(input),
    "Potential injection detected"
  )
})
```

### 8.3 Execution Security

**Approval Mechanisms**:
- Command allowlists per agent (regex patterns)
- Risk-based gating (high-risk commands require approval)
- 5-minute approval window with auto-expiry
- Circuit breaker on repeated denials

### 8.4 Secrets & Credentials

**Secret Scanning** (`/lib/secret-scanner.ts`):
- Detect AWS/Azure/GCP API keys in configs
- Stripe test/live keys
- Generic API key patterns
- JWTs + OAuth tokens
- Database connection strings

**Secure Storage**:
- Hashed passwords (scrypt)
- Encrypted API keys (when stored)
- No secrets in audit logs

### 8.5 Audit Compliance

**Immutable Audit Trail**:
```
- Every mutation logged to audit_log
- Timestamps + actor + IP address
- Cannot be deleted (retention policy)
- Exportable for compliance reviews
```

---

## 9. API Reference (Key Routes)

### Agent Management
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/agents` | GET | viewer | List agents |
| `/api/agents` | POST | operator | Register agent |
| `/api/agents/[id]` | GET | viewer | Agent detail |
| `/api/agents/[id]` | PUT | operator | Update config |
| `/api/agents/[id]` | DELETE | admin | Archive |
| `/api/agents/[id]/heartbeat` | GET | viewer | Work items check |
| `/api/agents/[id]/wake` | POST | operator | Send message |
| `/api/agents/comms` | GET | viewer | Comms graph |

### Task Management
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/tasks` | GET | viewer | List tasks |
| `/api/tasks` | POST | operator | Create task |
| `/api/tasks/[id]` | GET | viewer | Task detail |
| `/api/tasks/[id]` | PUT | operator | Update |
| `/api/tasks/[id]/comments` | POST | operator | Add comment |
| `/api/tasks/queue` | GET | viewer | Pending queue |
| `/api/tasks/outcomes` | GET | viewer | Success metrics |

### Chat & Communication
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/chat/messages` | GET | viewer | Fetch thread |
| `/api/chat/messages` | POST | operator | Send message |
| `/api/chat/conversations` | GET | viewer | List conversations |

### Control & Execution
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/exec-approvals` | GET | operator | Pending requests |
| `/api/exec-approvals` | POST | operator | Respond to request |

### Real-Time Events
| Endpoint | Protocol | Auth | Purpose |
|----------|----------|------|---------|
| `/api/events` | SSE | operator | Event stream |
| `ws://...` | WebSocket | operator | Gateway RPC + broadcast |

---

## 10. Code Examples

### 10.1 Agent Registration

```typescript
// POST /api/agents
const response = await fetch('/api/agents', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'code-reviewer',
    role: 'quality_gate',
    template: 'reviewer',
    model: 'opus'
  })
})

const agent = await response.json()
console.log(`Agent ${agent.name} registered with ID ${agent.id}`)
```

### 10.2 Task Creation & Assignment

```typescript
// 1. Create task
const taskRes = await fetch('/api/tasks', {
  method: 'POST',
  body: JSON.stringify({
    title: 'Review PR #432',
    description: 'Check code quality and test coverage',
    priority: 'high',
    assigned_to: 'code-reviewer',
    due_date: Math.floor(Date.now() / 1000) + 86400  // Tomorrow
  })
})

const task = await taskRes.json()

// 2. Monitor via activity feed
const activitiesRes = await fetch('/api/activities?entity_type=task&limit=20')
const activities = await activitiesRes.json()
activities.data.forEach(a => {
  console.log(`[${new Date(a.created_at * 1000).toISOString()}] ${a.actor}: ${a.description}`)
})

// 3. Check task outcomes
const outcomeRes = await fetch('/api/tasks/outcomes?timeframe=7d')
const outcomes = await outcomeRes.json()
console.log(`Success rate: ${outcomes.stats.success / outcomes.stats.total * 100}%`)
```

### 10.3 Agent Communication

```typescript
// Send message to agent
const msgRes = await fetch('/api/agents/builder/message', {
  method: 'POST',
  body: JSON.stringify({
    content: '@builder Please review the failing tests in src/',
    message_type: 'text'
  })
})

// Subscribe to comms feed (SSE)
const eventSource = new EventSource('/api/events')
eventSource.addEventListener('chat.message', (event) => {
  const msg = JSON.parse(event.data)
  console.log(`${msg.from_agent} → ${msg.to_agent}: ${msg.content}`)
})
```

### 10.4 WebSocket Integration (Browser)

```typescript
const ws = new WebSocket('wss://localhost:3100/api/gateways/connect?token=...')

ws.onmessage = (event) => {
  const frame = JSON.parse(event.data)
  
  if (frame.type === 'event') {
    switch (frame.event) {
      case 'agent.status':
        console.log(`Agent ${frame.payload.id}: ${frame.payload.status}`)
        break
      case 'task.updated':
        console.log(`Task ${frame.payload.id} → ${frame.payload.status}`)
        break
      case 'chat.message':
        console.log(`${frame.payload.from_agent}: ${frame.payload.content}`)
        break
    }
  }
}

// Send heartbeat ping every 30s
setInterval(() => {
  ws.send(JSON.stringify({ type: 'ping', id: Date.now() }))
}, 30000)
```

### 10.5 Skill Installation & Security Scanning

```typescript
// GET /api/skills - List installed skills
const skillsRes = await fetch('/api/skills')
const { adapters } = await skillsRes.json()

// POST /api/skills - Install skill
const installRes = await fetch('/api/skills', {
  method: 'POST',
  body: JSON.stringify({
    source: 'github',
    owner: 'openclaw',
    repo: 'skills',
    name: 'search-web',
    version: 'v1.0.0'
  })
})

const installed = await installRes.json()
console.log(`Security status: ${installed.security_status}`)  // 'safe' | 'flagged'
```

### 10.6 Webhook Configuration

```typescript
// Create webhook
const whRes = await fetch('/api/webhooks', {
  method: 'POST',
  body: JSON.stringify({
    name: 'slack-notifications',
    url: 'https://hooks.slack.com/services/...',
    events: [
      'agent.created',
      'task.status_changed',
      'security.flagged'
    ]
  })
})

const webhook = await whRes.json()

// Verify signature (Node.js)
import crypto from 'crypto'

function verifySignature(secret, rawBody, signatureHeader) {
  const [algo, expected] = signatureHeader.split('=')
  const computed = crypto
    .createHmac('sha256', secret)
    .update(rawBody)
    .digest('hex')
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(computed))
}
```

---

## 11. Deployment & Operations

### Configuration

**Environment Variables**:
```bash
# Database
MISSION_CONTROL_DATA_DIR=./.data
DATABASE_URL=sqlite:///.data/mission-control.db

# Gateway
OPENCLAW_GATEWAY_HOST=127.0.0.1
OPENCLAW_GATEWAY_PORT=18789
OPENCLAW_GATEWAY_TOKEN=...

# Auth
MC_ADMIN_PASSWORD=...              # First-time setup only
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Security
MC_ALLOWED_HOSTS=localhost,example.com
MC_COOKIE_SECURE=1                 # HTTPS only
MC_SESSION_TTL_HOURS=24

# Networking
NEXT_PUBLIC_GATEWAY_URL=wss://gateway.example.com
```

### First-Time Setup

```bash
git clone https://github.com/builderz-labs/mission-control.git
cd mission-control

pnpm install
pnpm build

# Generate first admin password
export MC_ADMIN_PASSWORD="change-me-on-first-login"

pnpm dev  # http://localhost:3100
```

### Database Backups

```bash
# POST /api/backup
curl -X POST http://localhost:3100/api/backup \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json"

# Returns: { backup_path: ".data/backups/mission-control-2026-06-02-120000.db" }
```

---

## 12. Summary: Key Insights

| Aspect | Approach |
|--------|----------|
| **Agent Control** | REST API + WebSocket RPC to distributed gateway |
| **Communication** | Event bus (pub/sub) → SSE + WS → clients |
| **Data** | SQLite (WAL) with 45 migrations, workspace isolation |
| **Security** | RBAC, injection prevention, execution approval gates |
| **Monitoring** | Real-time dashboards, immutable audit log, activity stream |
| **Scalability** | Multi-gateway support, rate limiting, adapter pattern |
| **Integration** | Webhooks (HMAC-signed), skill registry, framework adapters |
| **Cost Tracking** | Per-model, per-agent token accounting with USD estimates |

---

**Last Updated**: June 2, 2026  
**Architecture Version**: 2.1+  
**API Endpoints**: 101 REST routes + WebSocket + SSE  
**Database Schema**: 45 migrations, 35+ tables  
**Test Coverage**: 165 unit + 295 E2E tests

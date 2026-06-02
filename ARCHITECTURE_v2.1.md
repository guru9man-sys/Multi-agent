# System Architecture - Production Grade (v2.1)

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Streamlit Dashboard (localhost:8501)                                       │
│  ┌──────────────┬───────────────┬──────────────┬───────────────┬──────────┐ │
│  │ Tab 1: DAG   │ Tab 2: Tokens │ Tab 3: Health│ Tab 4: Trace  │Tab 5:Ctrl│ │
│  │  Flow        │ Analytics     │ & Metrics    │ Viewer        │Center   │ │
│  └──────────────┴───────────────┴──────────────┴───────────────┴──────────┘ │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │ Tab 6: ⚙️ Prompt Management (NEW!)                                        ││
│  │ ┌─────────────────────────────────────────────────────────────────────┐  ││
│  │ │ Agent: [knowledge_architect ▼]  🔄 Refresh                        │  ││
│  │ ├─────────────────────────────────────────────────────────────────────┤  ││
│  │ │ Temp: 0.7   Version: 1                                             │  ││
│  │ ├──────────────────────┬──────────────────────────────────────────────┤  ││
│  │ │ ✏️ Edit              │ 📄 Preview                                   │  ││
│  │ ├─────────────────────────────────────────────────────────────────────┤  ││
│  │ │ [System Prompt Text Area - 200px height]                           │  ││
│  │ │ Temperature: 0.7 ☰──────────                                        │  ││
│  │ │ Max Tokens: [2000]                                                 │  ││
│  │ ├─────────────────────────────────────────────────────────────────────┤  ││
│  │ │ 💾 Save Changes  │ ❌ Discard  │ ⏮️ Rollback                        │  ││
│  │ └─────────────────────────────────────────────────────────────────────┘  ││
│  └──────────────────────────────────────────────────────────────────────────┘│
│                                                                               │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ HTTP REST (port 8000)
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                           API LAYER (FastAPI)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ Endpoints (Existing):           Endpoints (NEW):                           │
│ • POST /chat                     • GET /agents/list                        │
│ • POST /control/execute          • GET /agents/{id}/config                 │
│ • POST /control/session          • POST /agents/{id}/config                │
│ • POST /control/settings         • POST /agents/{id}/config/rollback       │
│ • GET /obs/tasks                                                           │
│ • GET /obs/tasks/{id}/trace                                               │
│ • GET /obs/metrics/summary                                                │
│ • WebSocket /ws/{session_id}                                              │
│                                                                               │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ Orchestration
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                    ORCHESTRATION LAYER (NEW: Resilience)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  AgentOrchestrator                                                          │
│  ├─ handle_request()         [Router triage]                              │
│  │  │                                                                      │
│  │  └─→ _execute_dag_async() [DAG execution with dependencies]           │
│  │       │                                                                │
│  │       └─→ _execute_agent_async() [Wrapped with @retry_async]  (NEW!)  │
│  │           │                                                            │
│  │           │ ┌──────────────────────────────────────────┐              │
│  │           │ │ @retry_async decorator (NEW)            │              │
│  │           │ ├──────────────────────────────────────────┤              │
│  │           │ │ • Attempt 1/6: Try agent execution      │              │
│  │           │ │ • Transient error? → Wait 1.23s + retry │              │
│  │           │ │ • Rate limit (429)? → Honor Retry-After │              │
│  │           │ │ • Auth error (401)? → Fail immediately  │              │
│  │           │ │ • Success? → Return response            │              │
│  │           │ │                                          │              │
│  │           │ │ Presets Available:                       │              │
│  │           │ │ • CONFIG_API_CALL (1-30s, 5 retries)   │              │
│  │           │ │ • CONFIG_DATABASE (0.5-10s, 3 retries) │              │
│  │           │ │ • CONFIG_CRITICAL (2-60s, 7 retries)   │              │
│  │           │ └──────────────────────────────────────────┘              │
│  │           │                                                            │
│  │           └─→ Agent Implementation                                    │
│  │                                                                        │
│  ├─ cloud_brain (for routing decisions)                                  │
│  ├─ meta_brain (for DAG optimization suggestions)                        │
│  └─ db_manager (for persistence - see below)                             │
│                                                                             │
│  Error Recovery Flow:                                                      │
│  TimeoutError → Retry with backoff → Success                              │
│  RateLimitError (429) → Honor Retry-After → Success                      │
│  AuthError (401) → Fail fast → Return error                              │
│  NetworkError → Retry with exponential backoff → Success                 │
│                                                                             │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ Agent Tasks
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                        AGENT LAYER (8 Specialized Agents)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │ Knowledge        │  │ Integrative      │  │ Social Media     │          │
│  │ Architect        │  │ Synthesis Expert │  │ Mastery          │          │
│  │ (Research)       │  │ (Combine)        │  │ (Content)        │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │ Self-Evolving    │  │ QA Auditor       │  │ Visual Designer  │          │
│  │ SRE              │  │ (Quality Check)  │  │ (UI/UX)          │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│  ┌──────────────────┐  ┌──────────────────┐                                │
│  │ Booking Agent    │  │ Accounting Agent │                                │
│  │ (Appointments)   │  │ (Finance)        │                                │
│  └──────────────────┘  └──────────────────┘                                │
│                                                                               │
│  Each agent receives:                                                       │
│  • TaskRequest with instruction & context                                   │
│  • Access to prior step artifacts (dependency context)                      │
│  • Returns TaskResponse with artifacts & metadata                           │
│                                                                               │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ Data Operations
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                  DATA PERSISTENCE LAYER (NEW: Validation)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  DBManager (SQLite)                                                         │
│  │                                                                          │
│  ├─ create_task(task_data)                                                │
│  │  ├─ _validate_payload() (NEW!)  ← Check 'instruction' or similar      │
│  │  │  └─ Valid? → Save to DB                                            │
│  │  │  └─ Invalid? → Rollback + Error                                    │
│  │  └─ ✓ TaskRecord saved                                                │
│  │                                                                        │
│  ├─ save_artifact(task_id, artifact_data)                               │
│  │  ├─ _validate_artifacts() (NEW!)  ← Check 'artifacts' field present  │
│  │  │  └─ Valid? → Save to DB                                            │
│  │  │  └─ Invalid? → Rollback + Error                                    │
│  │  └─ ✓ ArtifactRecord saved                                            │
│  │                                                                        │
│  ├─ update_task_status()                                                 │
│  ├─ get_task_trace()                                                     │
│  └─ get_performance_metrics()                                            │
│                                                                             │
│  Database Schema (SQLite):                                                 │
│  ├─ TaskRecord                   [Validated at creation]                  │
│  ├─ ArtifactRecord               [Validated at creation]                  │
│  ├─ LogRecord                                                             │
│  ├─ ExecutionMetricsRecord                                               │
│  ├─ ConversationMemory                                                    │
│  ├─ UserPreference                                                        │
│  ├─ AppointmentRecord                                                     │
│  └─ AccountingRecord                                                      │
│                                                                             │
│  Validation Logic:                                                         │
│  TaskPayload:       Must have 'instruction' OR 'user_input' OR 'content' │
│  Artifacts:         Must have non-empty 'artifacts' dict field           │
│  On Validation Fail: Automatic rollback + Exception thrown               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram: Request to Response

```
┌──────────────────────────┐
│ User Input (Dashboard)   │
│ "Research topic X"       │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ API Server                       │
│ POST /chat                       │
├──────────────────────────────────┤
│ • Create session if needed       │
│ • Parse request                  │
│ • Pass to Orchestrator           │
└────────┬───────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Router (LocalRouter/HybridRouter)│
├──────────────────────────────────┤
│ • Classify intent                │
│ • Determine if local or cloud    │
│ • Select target agent(s)         │
└────────┬───────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ DAG Execution (_execute_dag_async)│
├──────────────────────────────────┤
│ • Plan execution order           │
│ • Track dependencies             │
│ • Execute steps in parallel      │
└────────┬───────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Per-Step Agent Execution         │
│ _execute_agent_async() (STEP 1)  │
├──────────────────────────────────┤
│ @retry_async decorator           │
│   ├─ Attempt 1                   │
│   │  ├─ Execute agent            │
│   │  ├─ Success? → Return        │
│   │  └─ Transient error? → Wait  │
│   ├─ Attempt 2 (after 1.23s)     │
│   │  ├─ Execute agent            │
│   │  └─ Success? → Return        │
│   └─ ... (up to 5 retries)       │
└────────┬───────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Agent Execution (e.g., Research) │
├──────────────────────────────────┤
│ • KnowledgeArchitect runs        │
│ • Produces artifacts             │
│ • Returns TaskResponse           │
└────────┬───────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Save Artifacts to Database       │
│ save_artifact()                  │
├──────────────────────────────────┤
│ @validate_artifacts decorator   │
│   ├─ Check 'artifacts' field    │
│   ├─ Valid? → Commit to DB      │
│   └─ Invalid? → Rollback + Error│
└────────┬───────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Next DAG Step (if any)           │
│ Inject step_1 artifacts as       │
│ dependency context               │
└────────┬───────────────────────────┘
         │ (repeat for all steps)
         │
         ▼
┌──────────────────────────────────┐
│ Aggregate Results                │
│ Combine all step outputs         │
└────────┬───────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Return Response                  │
│ • Status (success/failure)       │
│ • Artifacts from all steps       │
│ • Token usage                    │
│ • Execution time                 │
└────────┬───────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Display on Dashboard             │
│ • Update task status             │
│ • Show artifacts                 │
│ • Display execution trace        │
│ • Render visualizations          │
└──────────────────────────────────┘
```

---

## Resilience Layer - Retry Logic Flow

```
                    ┌─────────────────────┐
                    │ _execute_agent_async│
                    │     (Called)        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  @retry_async       │
                    │   decorator         │
                    └──────────┬──────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
            Attempt 1              Attempt 2 (after delay)
         ┌──────────────┐        ┌──────────────┐
         │ Try execution│        │ Try execution│
         └──────┬───────┘        └──────┬───────┘
                │ Success?              │ Success?
            YES │                   YES │
            ┌───▼──────┐            ┌───▼──────┐
            │ Return   │            │ Return   │
            │ Response │            │ Response │
            └──────────┘            └──────────┘
                │ Failure               │ Failure
            NO  │                   NO  │
            ┌───▼────────────────────────┬───┐
            │ Error Type?                │   │
            ├─────────────────┬──────────┤   │
            │                 │          │   │
        Auth Error        Transient    Rate
        (401, 403)        Error       Limit
            │              (Timeout)   (429)
            │                 │          │
            ▼                 ▼          ▼
        Fail Fast       ┌─────────┐  ┌──────────┐
        Return          │ Honor   │  │ Check    │
        Error           │ Retry-  │  │ Retry-   │
                        │ After   │  │ After    │
                        │ Header  │  │ Header   │
                        └────┬────┘  └────┬─────┘
                             │            │
                             └─────┬──────┘
                                   │
                        ┌──────────▼────────────┐
                        │ Calculate Backoff     │
                        │ delay = 1.0s * 2^retry│
                        │ + jitter              │
                        │ max_delay = 30s       │
                        └──────────┬────────────┘
                                   │
                        ┌──────────▼────────────┐
                        │ Sleep                 │
                        │ (1.23s, 2.46s, ...)  │
                        └──────────┬────────────┘
                                   │
                        ┌──────────▼────────────┐
                        │ Ready for next retry? │
                        │ attempt < max_retries?│
                        └──────────┬────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │ YES                    NO   │
                    ▼                             ▼
              Attempt N+1            All Retries Exhausted
               (continue)             Raise Exception
                                      User sees: ❌ Failed
                                      Logger shows: Failed after N retries
```

---

## Validation Layer - Data Integrity Flow

```
┌─────────────────────────────────────────────────────────┐
│ Method: create_task() or save_artifact()                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Receive Data (dict)          │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Validate Structure           │
        │ • Is dict?                   │
        │ • Has required fields?       │
        └──────────────┬───────────────┘
                       │
        ┌──────────────┴────────────────┐
        │ Validation Result             │
        ├──────────────┬────────────────┤
        │   VALID      │    INVALID     │
        ▼              ▼                │
    ┌──────┐      ┌────────┐           │
    │ Save │      │ Raise  │           │
    │ to   │      │ Error  │           │
    │ DB   │      └───┬────┘           │
    └───┬──┘          │                │
        │             ▼                │
        │      ┌──────────────┐        │
        │      │ Rollback     │        │
        │      │ Transaction  │        │
        │      └──────────────┘        │
        │             │                │
        ▼             ▼                │
    Success        Rollback            │
    ✓ Task/       ✗ No data            │
      Artifact     saved               │
      saved        Error               │
               returned to               │
               caller                    │
                                         │
  Log: ✓ Task created                 │
       ✗ Failed to save artifact       │
       
Example Validation Rules:
─────────────────────────────

create_task():
  payload must have:
  • 'instruction' OR
  • 'user_input' OR  
  • 'content'
  
  Examples:
  ✓ VALID:   {"instruction": "Research X"}
  ✓ VALID:   {"user_input": "Book appointment"}
  ✗ INVALID: {} (missing all three)
  ✗ INVALID: {"other_field": "value"}

save_artifact():
  artifact_data must have:
  • 'artifacts' field (dict, non-empty)
  • 'meta' field (with confidence)
  
  Examples:
  ✓ VALID:   {"artifacts": {"result": "..."}, "meta": {...}}
  ✗ INVALID: {"artifacts": {}} (empty)
  ✗ INVALID: {"meta": {...}} (missing artifacts)
```

---

## Prompt Management - Real-Time Configuration

```
Dashboard User                          Backend System
│                                      │
├─ Opens Tab 6                        │
├─ Sees agent dropdown                │
├─ Selects "knowledge_architect"      │
│                                     ├─ GET /agents/{id}/config
│                                     │ Returns: system_prompt, version, etc.
│◄────────────────────────────────────┤
│ Displays current prompt             │
│ Shows temperature: 0.7              │
│ Shows version: 1                    │
│                                     │
├─ Clicks "Edit" tab                  │
├─ Modifies system prompt text        │
├─ Adjusts temperature slider         │
├─ Changes max_tokens value           │
│                                     │
├─ Clicks "Save Changes"              │
│                                     ├─ POST /agents/{id}/config
│                                     │ Receives: new_prompt, temp, tokens
│                                     │ Updates in-memory config
│                                     │ Returns: success, new_version: 2
│◄────────────────────────────────────┤
│ Shows: "✅ Configuration updated"   │
│ Version now shows: 2                │
│                                     │
├─ (Optional) Clicks "Rollback"       │
│                                     ├─ POST /agents/{id}/config/rollback
│                                     │ Reverts to version 1
│                                     │ Returns: rolled_back_at, prev_version
│◄────────────────────────────────────┤
│ Shows: "⏮️ Configuration rolled back"│
│ Version now shows: 1                │
│                                     │
├─ Next agent execution uses:         │
│  - New prompt (or rolled back)       │
│  - New temperature                  │
│  - New max_tokens                   │
│  (Takes effect immediately!)        │
│                                     │

Key Benefit: 
Zero downtime configuration changes!
No restart required.
Changes apply to next task execution.
```

---

## Summary: What's New in v2.1?

| Component | Capability | Benefit |
|-----------|-----------|---------|
| **Resilience** | Auto-retry with exponential backoff | Survive transient failures (429, timeout) |
| **Resilience** | Rate-limit aware (429 handling) | Respect API rate limits gracefully |
| **Resilience** | Circuit breaker patterns | Prevent cascading failures |
| **Validation** | JSON schema validation | Prevent corrupted data in database |
| **Validation** | Automatic transaction rollback | Maintain data consistency on errors |
| **Validation** | Comprehensive error logging | Easy debugging of data issues |
| **Prompt Mgmt** | Real-time agent configuration | No restart needed for config changes |
| **Prompt Mgmt** | Web UI for prompt editing | User-friendly configuration management |
| **Prompt Mgmt** | Rollback functionality | Easy recovery from bad changes |
| **API** | RESTful endpoints | Programmatic access to config |

---

**Status**: ✅ Production-Ready (v2.1)  
**All Systems**: Operational  
**Ready to Deploy**: Yes

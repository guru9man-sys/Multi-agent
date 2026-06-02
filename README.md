# Multi-Agent System (AgentOS)

A production-ready orchestration system for coordinating specialized AI agents to perform complex, multi-step tasks with minimal cloud token consumption.

**🆕 Phase 7.4**: Now supports **configurable Local LLM selection** - choose any Ollama or vLLM model with zero code changes!

## Architecture Overview

```
User Input
    ↓
Local Router (Configurable LLM) - Zero-Token Triage
    ├─ Phase 7.4: Qwen 2.5 | Llama 3 | Mistral | Custom Models
    ├─ Provider: Ollama | vLLM | Extensible
    └─ Fallback: Cloud LLM (OpenAI/Gemini)
    ↓
Decision: Simple or Complex?
    ├─→ [SIMPLE] → Assign to Agent Directly
    └─→ [COMPLEX] → Cloud Brain (Decompose into DAG)
         ↓
        Execute DAG (Dependency-aware execution)
         ├→ Knowledge Architect (Research)
         ├→ Synthesis Expert (Analysis)
         ├→ Social Media Mastery (Content)
         └→ SRE Agent (Monitoring)
    ↓
    Save to SQLite Database
    ↓
    Return Results to User
```

## 🆕 Phase 7.4: Configurable Local LLM Selection

### What's New?
- ✅ Support for multiple LLM providers (Ollama, vLLM)
- ✅ Dynamic model selection via `.env` (no code changes)
- ✅ Factory pattern for extensibility
- ✅ Health checking and graceful degradation
- ✅ Comprehensive documentation and tests

### Quick Setup (5 minutes)
```bash
# 1. Install Ollama and pull a model
ollama pull qwen2.5

# 2. Start Ollama
ollama serve

# 3. Configure .env
cp .env.example .env
# Edit LOCAL_LLM_MODEL=qwen2.5  (or llama3, mistral, etc.)

# 4. Test
python test_local_llm_selection.py

# 5. Run
python orchestrator_main.py
```

### Supported Models
| Provider | Models | Recommended |
|----------|--------|------------|
| **Ollama** | qwen2.5, llama3, mistral, phi, neural-chat | ✅ Qwen 2.5 |
| **vLLM** | Llama 2/3, Mistral, Falcon, Qwen | ✅ Llama 2 7B |

See [`PHASE_7_4_QUICK_START.md`](PHASE_7_4_QUICK_START.md) for detailed setup instructions.

## Components

### 1. **Schemas** (`schemas.py`)
Strict Pydantic models that enforce data contracts across all agents.
- `TaskRequest`: The envelope sent to agents
- `TaskResponse`: The envelope returned from agents
- `RoutingDecision`: Output from the local router
- `MasterPlan`: High-level plan from Cloud Brain

### 2. **Database** (`database.py`)
SQLite-based memory layer for persistent state.
- `TaskRecord`: Stores task lifecycle
- `ArtifactRecord`: Stores agent outputs
- `LogRecord`: Audit trail of all transitions
- `DBManager`: Connection management and CRUD operations

### 3. **Validator** (`validator.py`)
Ensures LLM outputs conform to schemas before entering the pipeline.
- `ResponseValidator`: Cleans and validates JSON from local/cloud LLMs
- Handles messy formatting from local LLMs automatically

### 4. **Router** (`router.py`)
Local routing using Qwen 2.5 to save cloud tokens.
- `LocalRouter`: Routes requests to appropriate agents
- `HybridRouter`: Escalates complex requests to Cloud Brain
- ZERO cloud token usage for simple requests

### 5. **Cloud Brain** (`cloud_brain.py`)
Decomposes complex requests into executable DAGs.
- Uses Claude (or other cloud LLM) for high-reasoning tasks
- Generates Directed Acyclic Graphs (DAGs) with dependencies
- Only invoked when needed (saves tokens)

### 6. **Knowledge Architect** (`knowledge_architect.py`)
The Researcher Agent - gathers information and creates knowledge maps.
- Web search integration (Tavily API)
- Generates Mermaid diagrams
- Extracts key facts from multiple sources

### 7. **Synthesis Expert** (`synthesis_expert.py`)
The Analyst Agent - finds contradictions and systemic links.
- Analyzes artifacts from Knowledge Architect
- Identifies contradictions in sources
- Maps systemic relationships
- Creates executive summaries

### 8. **Social Media Mastery** (`social_mastery.py`)
The Content Agent - creates high-conversion social media posts.
- Platform-specific adaptation (LinkedIn, X, TikTok, Facebook, Line)
- Generates hooks, body copy, CTAs, and hashtags
- A/B variant generation capability

### 9. **SRE Agent** (`sre_agent.py`)
The Guardian Agent - monitors and fixes system issues.
- Tracks failure patterns
- Detects agent degradation
- Proposes self-healing fixes
- Generates health reports

### 10. **Orchestrator** (`orchestrator_main.py`)
The Master Conductor - coordinates all agents.
- Main entry point for requests
- Routes to appropriate agents
- Executes complex DAGs
- Manages end-to-end workflows

## Installation

```bash
# Clone or navigate to the project directory
cd agents_system

# Install dependencies
pip install -r requirements.txt

# Create .env file for API keys
cp .env.example .env
```

### .env Configuration

```env
# API Keys
TAVILY_API_KEY=your_tavily_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Local LLM (Ollama)
LOCAL_LLM_ENDPOINT=http://localhost:11434
LOCAL_LLM_MODEL=qwen2.5

# Database
DATABASE_URL=sqlite:///agent_system.db

# Environment
ENV=development
```

## Quick Start

### 1. Simple Usage

```python
from database import DBManager
from orchestrator_main import AgentOrchestrator
from schemas import TaskPriority

# Initialize
db = DBManager()
orchestrator = AgentOrchestrator(db, {
    "tavily_api_key": "YOUR_API_KEY"
})

# Simple request
result = orchestrator.handle_request(
    "Create a LinkedIn post about AI trends",
    priority=TaskPriority.HIGH
)

print(result)
```

### 2. Complex Request (with DAG decomposition)

```python
# Complex request - triggers Cloud Brain
result = orchestrator.handle_request(
    """
    Research the latest findings on longevity,
    analyze if there are contradictions,
    and create viral content for LinkedIn and Twitter.
    """
)

# Result includes all intermediate steps
print(result['results'])
```

### 3. System Health Check

```python
health = orchestrator.get_system_health()
print(f"Status: {health['health_status']}")
print(f"Degraded Agents: {health['degraded_agents']}")
print(f"Metrics: {health['agent_metrics']}")
```

## Token Efficiency Strategy

### Phase 1: Local Routing (0 cloud tokens)
- Qwen 2.5 analyzes the request
- Routes to appropriate agent
- Saves decision to database

### Phase 2: Simple Task Execution (Variable)
- 90% of requests can be handled by a single agent
- Each agent uses cloud LLM efficiently
- Results cached in SQLite

### Phase 3: Complex Task Decomposition (One-time cloud cost)
- Only triggered when `escalate_to_cloud=True`
- Cloud LLM creates a DAG once
- DAG is then executed sequentially
- No redundant cloud calls

## Database Schema

```sql
-- Tasks Table
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    priority TEXT,
    agent_role TEXT,
    action TEXT,
    status TEXT,
    payload JSON,
    constraints JSON,
    created_at DATETIME,
    updated_at DATETIME,
    escalated_to_cloud BOOLEAN,
    parent_task_id TEXT
);

-- Artifacts Table
CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY,
    task_id TEXT FOREIGN KEY,
    content JSON,
    confidence FLOAT,
    meta JSON,
    created_at DATETIME
);

-- Logs Table
CREATE TABLE logs (
    log_id TEXT PRIMARY KEY,
    task_id TEXT FOREIGN KEY,
    old_status TEXT,
    new_status TEXT,
    reason TEXT,
    created_at DATETIME
);
```

## Agent Responsibilities

| Agent | Input | Output | Cost |
|-------|-------|--------|------|
| **Knowledge Architect** | Query | Research + Diagram | Cloud LLM |
| **Synthesis Expert** | Artifacts | Analysis + Contradictions | Cloud LLM |
| **Social Media Mastery** | Synthesis | Content (5 platforms) | Cloud LLM |
| **SRE Agent** | System Logs | Health Report + Fixes | Cloud LLM (occasional) |

## Workflow Examples

### Example 1: Simple Content Creation
```
User: "Create a TikTok script about fitness"
└─→ Router: "This is for Social Media Mastery" (confidence: 0.95)
    └─→ Social Media Mastery: Creates script
        └─→ Result: TikTok video script
```

### Example 2: Complex Campaign
```
User: "Research probiotics, analyze contradictions, create campaign"
└─→ Router: "This is complex" (confidence: 0.6, escalate: true)
    └─→ Cloud Brain: Decomposes into 3 steps
        ├─→ Step 1: Knowledge Architect researches probiotics
        ├─→ Step 2: Synthesis Expert analyzes contradictions
        └─→ Step 3: Social Media creates content for LinkedIn/X/TikTok
            └─→ Result: Full campaign ready to launch
```

## Error Handling

All failures are logged and tracked:
- Failed tasks create a LogRecord
- SRE Agent monitors failures
- Proposes fixes automatically
- System learns from mistakes

## Testing

```bash
# Run example usage
python example_usage.py

# This demonstrates:
# 1. Simple task execution
# 2. Complex DAG execution
# 3. System health monitoring
# 4. Database inspection
```

## Performance Metrics

- **Local Routing**: ~100ms (local LLM)
- **Simple Task**: ~2-5 seconds (single cloud LLM call)
- **Complex DAG**: ~10-30 seconds (multiple sequential calls)
- **Database Operations**: <100ms

## Future Enhancements

- [ ] Streaming responses for real-time feedback
- [ ] Advanced caching with Redis
- [ ] Multi-user support
- [ ] Rate limiting and quota management
- [ ] Webhook integrations
- [ ] REST API wrapper
- [ ] Web UI dashboard
- [ ] Analytics and insights

## Contributing

This is a reference implementation. Feel free to extend it for your specific use case.

## License

MIT License - Use freely for any purpose.

## Support

For issues or questions, refer to the inline documentation in each module.

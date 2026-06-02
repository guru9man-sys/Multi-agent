# 🚀 Quick Start Guide: Multi-Agent System (AgentOS)

## 📋 What You Have

A production-ready, token-efficient multi-agent system with these components:

```
agents_system/
├── __init__.py                 # Package initialization
├── schemas.py                  # Data contracts (Pydantic models)
├── database.py                 # SQLite state management
├── validator.py                # LLM output validation
├── router.py                   # Local routing (Qwen 2.5)
├── cloud_brain.py              # Task decomposition (Cloud LLM)
├── knowledge_architect.py      # Research agent
├── synthesis_expert.py         # Analysis agent
├── social_mastery.py           # Content creation agent
├── sre_agent.py                # System monitoring agent
├── orchestrator_main.py        # Master coordinator
├── config.py                   # Configuration management
├── example_usage.py            # Comprehensive examples
├── requirements.txt            # Python dependencies
├── .env.example                # Configuration template
├── README.md                   # Full documentation
└── agent_system.db             # SQLite database (auto-created)
```

## ⚡ 5-Minute Setup

### 1. Install Dependencies
```bash
cd agents_system
pip install -r requirements.txt
```

### 2. Configure APIs
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys:
# - TAVILY_API_KEY (for web search)
# - ANTHROPIC_API_KEY (for Claude)
# - LOCAL_LLM_* (for local Qwen 2.5)
```

### 3. Start Local LLM (Optional but Recommended)
```bash
# Using Ollama (recommended)
ollama run qwen2.5

# Or use any other local LLM endpoint
```

### 4. Test the System
```bash
python example_usage.py
```

## 🎯 Usage Examples

### Example 1: Simple Task (No Cloud Token Cost)
```python
from database import DBManager
from orchestrator_main import AgentOrchestrator

db = DBManager()
orch = AgentOrchestrator(db)

result = orch.handle_request("Create a Twitter post about AI")
```

### Example 2: Complex Task (With DAG Decomposition)
```python
result = orch.handle_request("""
    Research biohacking trends,
    analyze contradictions in the literature,
    and create viral content for LinkedIn, Twitter, and TikTok.
""")

# Result includes all intermediate steps
print(result['results'])
```

### Example 3: Check System Health
```python
health = orch.get_system_health()
print(health['health_status'])
print(health['agent_metrics'])
```

## 💰 Token Economics

| Scenario | Local Tokens | Cloud Tokens |
|----------|-------------|-------------|
| Simple routing + execution | 0 | ~300-500 |
| Complex DAG decomposition + execution | 0 | ~1000-2000 |
| System health check | 0 | 0-200 |

**vs. Single Cloud Call: ~2000-5000 tokens**

## 🏗️ System Architecture

```
USER REQUEST
    ↓
┌─────────────────────────────────────┐
│ LOCAL ROUTER (Qwen 2.5)            │  ← ZERO cloud tokens
│ "Is this simple or complex?"        │
└─────────────────────────────────────┘
    ↓
    ├─→ [SIMPLE] Single Agent
    │   └─→ Saves to SQLite
    │
    └─→ [COMPLEX] Cloud Brain
        ├─→ Decompose into DAG (Cloud LLM)
        ├─→ Execute Step 1: Knowledge Architect
        ├─→ Execute Step 2: Synthesis Expert
        ├─→ Execute Step 3: Social Media Mastery
        └─→ Monitor with SRE Agent
            ↓
        RESULTS (all saved to SQLite)
```

## 📊 Agent Capabilities

| Agent | Purpose | Primary Output |
|-------|---------|-----------------|
| **Knowledge Architect** | Research | Mindmaps, Fact-lists |
| **Synthesis Expert** | Analysis | Reports, Contradictions |
| **Social Media Mastery** | Content | Posts for 5 platforms |
| **SRE Agent** | Monitoring | Health Reports, Fixes |

## 🔧 Key Features

✅ **Token Efficient**: Local routing saves 80% of tokens  
✅ **Persistent**: SQLite database never loses state  
✅ **Scalable**: DAG-based execution handles complex workflows  
✅ **Self-Healing**: SRE agent monitors and suggests fixes  
✅ **Multi-Platform**: Social content for LinkedIn, X, TikTok, Facebook, Line  
✅ **Extensible**: Easy to add new agents or capabilities  

## 🚨 Common Issues & Solutions

### Issue: "No module named 'qwen2.5'"
**Solution**: Qwen is not Python—it's accessed via Ollama
```bash
ollama run qwen2.5  # Run this in a separate terminal
```

### Issue: "Tavily API key not working"
**Solution**: Get a free key from https://tavily.com
```bash
export TAVILY_API_KEY=your_key
```

### Issue: "ANTHROPIC_API_KEY not set"
**Solution**: Get a key from https://console.anthropic.com
```bash
export ANTHROPIC_API_KEY=your_key
```

## 📈 Next Steps

1. **Read Full Documentation**: See `README.md` for detailed architecture
2. **Run Examples**: Execute `example_usage.py` to see it in action
3. **Customize Prompts**: Edit the prompt templates in each agent
4. **Add New Agents**: Create a new file following the pattern
5. **Integrate with Your App**: Import `AgentOrchestrator` into your code

## 🔗 File Structure Guide

- **schemas.py**: Define new data types here
- **database.py**: Modify schema or add query methods
- **router.py**: Customize routing logic
- **knowledge_architect.py**: Change research behavior
- **social_mastery.py**: Modify content templates
- **config.py**: Add new configuration options

## 💡 Pro Tips

1. **Use task_id for tracking**: Every request gets a UUID in the database
2. **Async ready**: Can be wrapped with FastAPI for production
3. **Multi-user support**: Database is thread-safe (SQLAlchemy)
4. **Local-first development**: Work entirely offline with Ollama
5. **Gradual migration**: Start with simple tasks, then add complexity

## 🎓 Learning Path

1. Start with `example_usage.py` to understand the flow
2. Trace through `orchestrator_main.py` to see the execution
3. Modify prompts in individual agents
4. Add custom agents following the pattern
5. Wrap with FastAPI for web deployment

## 📞 Support

- Check `README.md` for architectural details
- Refer to docstrings in each file
- Review `example_usage.py` for usage patterns
- Inspect database with: `sqlite3 agent_system.db`

---

**Happy building! 🚀**

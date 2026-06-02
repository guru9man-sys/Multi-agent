# Production Deployment Guide: Multi-Agent System

This document provides the necessary instructions to deploy and maintain the Multi-Agent System in a production environment.

## 🏗 Architecture Overview
The system uses a **Hybrid Router** architecture that combines local routing with a **Cloud Brain** for complex task decomposition.
- **Pipeline**: Research $\rightarrow$ Synthesis $\rightarrow$ Content $\rightarrow$ Audit.
- **Execution**: Asynchronous DAG-based execution using `asyncio`.
- **Persistence**: SQLite with a TTL-based caching layer in `DBManager`.
- **Observability**: Professional logging with rotating files, execution tracing (Trace IDs), and a System Health Dashboard.

## 🛠 Setup & Installation

### 1. Environment Requirements
- **Python**: 3.9+ (Recommended)
- **OS**: Linux/Windows/macOS
- **Dependencies**: See `requirements.txt`

### 2. Configuration
Create a `.env` file in the root directory with the following keys:
```env
TAVILY_API_KEY=your_tavily_key
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
QWEN_API_KEY=your_qwen_key
DATABASE_URL=sqlite:///agent_system.db
LOG_LEVEL=INFO
ENV=production
```

### 3. Installation
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .\.venv\Scripts\activate # Windows

# Install dependencies
pip install -r requirements.txt
```

## 🚀 Operation & Maintenance

### Running the System
The main entry point is `orchestrator_main.py`. You can integrate it into a FastAPI or Flask wrapper for API access.

### Health Monitoring
Run the health dashboard periodically to verify API connectivity and DB status:
```bash
python agents_system/system_health.py
```

### Key Rotation
To update API keys without restarting the service:
1. Update the `.env` file.
2. Call `orchestrator.rotate_api_keys()`.

### Log Analysis
Logs are stored in `agents_system/logs/system.log`. 
- **Trace IDs**: Use the `TraceID` in logs to follow a single request across multiple agents.
- **Secret Masking**: All API keys are automatically masked as `[MASKED]`.

## 🛡 Security & Hardening
- **Input Validation**: All requests are validated via Pydantic schemas in `schemas.py`.
- **Resilience**: API calls use exponential backoff retries.
- **Degradation**: The system automatically falls back from OpenAI $\rightarrow$ Gemini $\rightarrow$ Qwen $\rightarrow$ Local LLM.

## 📈 Scaling Recommendations
- **Database**: For high-concurrency production, migrate from SQLite to PostgreSQL.
- **Async Workers**: Consider moving from `asyncio.run_in_executor` to a distributed task queue like Celery if the load exceeds a single machine's capacity.
- **Caching**: Increase the TTL in `DBManager` for static research topics to reduce API costs.

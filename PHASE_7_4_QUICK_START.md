# 🚀 Phase 7.4 Quick Start Guide: Configurable Local LLM Selection

> **Version**: Phase 7.4  
> **Date**: April 28, 2026  
> **Status**: ✅ Complete

---

## ⚡ 5-Minute Setup

### Step 1: Install Ollama
```bash
# Download from https://ollama.ai
# macOS / Windows / Linux
# Then start the service:
ollama serve
```

### Step 2: Pull a Model
```bash
# In a new terminal:
ollama pull qwen2.5
# Or choose another model:
ollama pull llama3
ollama pull mistral
```

### Step 3: Configure .env
Copy the sample and update with your preferences:
```bash
cp .env.example .env
```

Edit `.env`:
```env
# Choose your Local LLM
LOCAL_LLM_PROVIDER=ollama
LOCAL_LLM_MODEL=qwen2.5    # ← Change this to any model you want
LOCAL_LLM_ENDPOINT=http://localhost:11434
USE_LOCAL_LLM_ROUTING=true
```

### Step 4: Test the Setup
```bash
python test_local_llm_selection.py
```

Expected output:
```
✓ Client created successfully
✓ Local LLM is available!
✓ Response generated successfully!
```

### Step 5: Run the System
```bash
python orchestrator_main.py
```

---

## 🎯 Common Use Cases

### Use Case 1: Switch to Llama 3
```env
LOCAL_LLM_MODEL=llama3
```
Then run:
```bash
ollama pull llama3
python test_local_llm_selection.py
```

### Use Case 2: Use vLLM instead of Ollama
First, install and start vLLM:
```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-hf \
  --port 8000
```

Then update `.env`:
```env
LOCAL_LLM_PROVIDER=vllm
LOCAL_LLM_MODEL=meta-llama/Llama-2-7b-hf
LOCAL_LLM_ENDPOINT=http://localhost:8000
```

### Use Case 3: Disable Local LLM (Use Cloud Only)
```env
USE_LOCAL_LLM_ROUTING=false
# System will automatically use OpenAI or Gemini for routing
```

### Use Case 4: Fast Lightweight Setup
```env
LOCAL_LLM_MODEL=phi
LOCAL_LLM_TIMEOUT=30  # Faster model
```
Then:
```bash
ollama pull phi
```

---

## 📊 Model Comparison

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| phi | 3B | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Fast routing |
| qwen2.5 | 7B | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **Recommended** |
| mistral | 7B | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Balanced |
| llama3 | 8B | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | High quality |

---

## 🔧 Architecture Changes

### Before (Phase 7.3)
```python
# LocalRouter always without LLM client
self.local_router = LocalRouter(db_manager)
# Falls back to Cloud LLM automatically
```

### After (Phase 7.4)
```python
# Create appropriate LLM client
llm_client = LocalLLMClientFactory.create_from_config(config)

# Pass to LocalRouter
self.local_router = LocalRouter(db_manager, llm_client=llm_client)
# Uses Local LLM with Graceful Degradation fallback
```

### Files Modified
1. ✅ `utils/llm_clients.py` - **NEW** (300+ lines)
2. ✅ `config.py` - Added 5 new configuration variables
3. ✅ `orchestrator_main.py` - Initialize Local LLM client
4. ✅ `.env.example` - Updated configuration template

---

## 💡 Key Benefits

✅ **Zero code changes** - Just update `.env`  
✅ **Multiple LLM support** - Ollama, vLLM, extensible to others  
✅ **Graceful degradation** - Falls back to Cloud LLM if Local LLM fails  
✅ **Performance monitoring** - Logger tracks all LLM interactions  
✅ **Easy switching** - Change models without restarting (via `.env`)

---

## 🐛 Troubleshooting

### Error: "Local LLM not available"
**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it:
ollama serve
```

### Error: "Model not found"
**Solution:**
```bash
# List available models
ollama list

# Pull the model you want
ollama pull qwen2.5
```

### Error: Timeout
**Solution:**
```env
# Increase timeout for slower hardware
LOCAL_LLM_TIMEOUT=120
```

---

## 📚 Example: Using the Factory Pattern

```python
from utils.llm_clients import LocalLLMClientFactory
from config import config

# Create client from configuration
client = LocalLLMClientFactory.create_from_config(config)

# Check if available
if client and client.is_available():
    # Generate response
    response = client.generate("What is 2+2?")
    print(response)
else:
    print("Local LLM not available, using Cloud LLM")
```

---

## 🎓 Next Steps

1. **Test with different models** - Try `llama3`, `mistral`, etc.
2. **Monitor performance** - Check logs for response times
3. **Set up automatic fallback** - Already built-in, just works!
4. **Extend support** - Add new providers to `LocalLLMClientFactory`

---

## 📋 Checklist

- [ ] Ollama installed and running
- [ ] At least one model pulled (`ollama pull qwen2.5`)
- [ ] `.env` file created and configured
- [ ] `test_local_llm_selection.py` runs successfully
- [ ] System initialized with local LLM client
- [ ] Routing decisions working with Local LLM

---

**Need help?** Check [PHASE_7_4_LOCAL_LLM_SELECTION.md](PHASE_7_4_LOCAL_LLM_SELECTION.md) for detailed documentation.

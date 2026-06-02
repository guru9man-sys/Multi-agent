#!/usr/bin/env python3
"""Phase 2.1: Verify Environment Configuration Loading"""

import os
from config import config
from dotenv import load_dotenv

print('[PHASE 2: Environment Setup]')
print('=' * 60)
print()

# Try to load .env if it exists
if os.path.exists(".env"):
    load_dotenv()
    print('[OK] .env file found and loaded')
else:
    print('[INFO] .env file not found (using defaults/env vars)')

print()
print('Current Configuration Values:')
print('-' * 60)

# Check critical keys
checks = {
    "DATABASE_URL": config.DATABASE_URL,
    "TAVILY_API_KEY": config.TAVILY_API_KEY,
    "ANTHROPIC_API_KEY": config.ANTHROPIC_API_KEY,
    "OPENAI_API_KEY": config.OPENAI_API_KEY,
    "GEMINI_API_KEY": config.GEMINI_API_KEY,
    "QWEN_API_KEY": getattr(config, "QWEN_API_KEY", None),
    "LOCAL_LLM_ENDPOINT": config.LOCAL_LLM_ENDPOINT,
    "LOCAL_LLM_MODEL": config.LOCAL_LLM_MODEL,
    "ENV": os.getenv("ENV", "development"),
    "DEBUG": config.DEBUG
}

all_configured = True
for key, value in checks.items():
    status = '✅' if value and 'your_' not in str(value) else '⚠️'
    if not value or 'your_' in str(value):
        all_configured = False
    print(f"{status} {key:20} : {value}")

print()
if all_configured:
    print('✅ SUCCESS: All environment variables are correctly configured!')
else:
    print('⚠️ WARNING: Some API keys are missing or using placeholders.')
    print('   Please create a .env file based on .env.example')

print()
print('Phase 2.1 Result: ' + ('PASSED' if all_configured else 'PARTIAL (Missing Keys)'))

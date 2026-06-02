"""
config.py - Configuration Management
Centralized configuration for the multi-agent system.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    DEBUG = False
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///agent_system.db")

    # API Keys
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    QWEN_API_KEY = os.getenv("QWEN_API_KEY")

    # Google API Settings
    GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    GOOGLE_SERVICE_ACCOUNT_INFO = os.getenv("GOOGLE_SERVICE_ACCOUNT_INFO")
    GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
    GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    GOOGLE_UPLOAD_DEFAULT_TARGET = os.getenv("GOOGLE_UPLOAD_DEFAULT_TARGET", "google_drive")
    
    # Local LLM Configuration
    LOCAL_LLM_PROVIDER = os.getenv("LOCAL_LLM_PROVIDER", "ollama")  # 'ollama' or 'vllm'
    LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "qwen2.5")  # e.g., qwen2.5, llama3, mistral
    LOCAL_LLM_ENDPOINT = os.getenv("LOCAL_LLM_ENDPOINT", "http://localhost:11434")
    LOCAL_LLM_TIMEOUT = int(os.getenv("LOCAL_LLM_TIMEOUT", "60"))
    USE_LOCAL_LLM_ROUTING = os.getenv("USE_LOCAL_LLM_ROUTING", "true").lower() == "true"

    # System Settings
    DEFAULT_PRIORITY = "medium"
    DEFAULT_PLATFORM = "linkedin"

    # Timeouts (in seconds)
    SEARCH_TIMEOUT = 10
    LLM_TIMEOUT = 30

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    def refresh_keys(self):
        """Reloads API keys from environment variables without restarting."""
        load_dotenv(override=True)
        self.TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        self.QWEN_API_KEY = os.getenv("QWEN_API_KEY")


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


# Select config based on environment
ENV = os.getenv("ENV", "development")
if ENV == "production":
    config = ProductionConfig()
else:
    config = DevelopmentConfig()

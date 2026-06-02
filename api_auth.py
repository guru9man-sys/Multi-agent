"""
api_auth.py - Phase 7.4: API Security Layer
Provides simple API Key authentication to protect the AgentOS endpoints.
"""

from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from config import config
from typing import Optional

# Define the header name for the API key
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: Optional[str] = Security(api_key_header)):
    """
    Validates the API key provided in the request header.
    In production, this would check against a database of valid keys.
    """
    # For now, we use a system-wide key defined in config.py
    # In a real scenario, you'd have a list of valid keys or a DB table
    valid_key = config.SYSTEM_API_KEY or "default_secret_key_123"
    
    if api_key_header == valid_key:
        return api_key_header
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials. Invalid API Key."
    )

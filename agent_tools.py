"""
agent_tools.py - Phase 7.3: Implementation of actual tools for agents.
Contains a set of utility tools that agents can call autonomously.
"""

import os
import requests
from typing import Dict, Any, List, Optional
from tool_registry import registry
from utils.logger import logger
from document_parser import parser

# =============================================================================
# 🛠️ UTILITY TOOLS
# =============================================================================

# =============================================================================
# 🛠️ UTILITY TOOLS
# =============================================================================

@registry.register_tool(name="calculate_advanced", category="math")
def calculate_advanced(expression: str) -> str:
    """
    Evaluates a mathematical expression. 
    Use this for complex calculations that require precision.
    """
    try:
        # Use a safe evaluation method instead of eval()
        # We use a simple whitelist of allowed characters for basic math
        allowed_chars = "0123456789.+-*/() "
        if not all(char in allowed_chars for char in expression):
            return "Error: Invalid characters in expression. Only numbers and basic operators (+, -, *, /, .) are allowed."
        
        # Use a restricted environment for eval
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Calculation error: {str(e)}"

@registry.register_tool(name="fetch_url_content", category="web")
def fetch_url_content(url: str) -> str:
    """
    Fetches the raw text content from a given URL.
    Useful for deep-diving into a specific page found during research.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text[:5000] # Limit to 5k chars for context window
    except Exception as e:
        return f"Failed to fetch URL {url}: {str(e)}"

@registry.register_tool(name="read_local_file", category="system")
def read_local_file(file_path: str) -> str:
    """
    Reads the content of a local file from the workspace.
    Use this to analyze project files, logs, or configuration.
    """
    try:
        if not os.path.exists(file_path):
            return f"Error: File {file_path} not found."
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"

@registry.register_tool(name="analyze_pdf", category="document")
def analyze_pdf(file_path: str) -> str:
    """
    Extracts text and tables from a PDF document.
    Use this for research papers, official reports, and manuals.
    """
    result = parser.parse_pdf(file_path)
    if "error" in result:
        return result["error"]
    
    return f"PDF Content:\n{result['full_text']}\n\nTables:\n{result['tables']}"

@registry.register_tool(name="analyze_excel", category="document")
def analyze_excel(file_path: str, sheet_name: Optional[str] = None) -> str:
    """
    Extracts data from an Excel file (.xlsx, .xls).
    Use this for financial data, spreadsheets, and structured lists.
    """
    result = parser.parse_excel(file_path, sheet_name)
    if "error" in result:
        return result["error"]
    
    if "sheets" in result:
        sheets_text = "\n\n".join([f"Sheet: {name}\n{data}" for name, data in result["sheets"].items()])
        return f"Excel Data:\n{sheets_text}"
    else:
        return f"Excel Data (Sheet: {result['sheet_name']}):\n{result['data']}"

@registry.register_tool(name="write_local_file", category="system")
def write_local_file(file_path: str, content: str) -> str:
    """
    Writes content to a local file.
    Use this to save reports, generate code, or update documentation.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing to file {file_path}: {str(e)}"

@registry.register_tool(name="get_system_stats", category="system")
def get_system_stats() -> Dict[str, Any]:
    """
    Retrieves current system performance metrics.
    Useful for SRE agent to monitor health.
    """
    import psutil
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "timestamp": datetime.now().isoformat()
    }

# Import datetime for the stats tool
from datetime import datetime

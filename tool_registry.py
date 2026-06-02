"""
tool_registry.py - Phase 7.3: Autonomous Tool Use (Agentic Tooling)
Provides a centralized registry for tools that agents can call dynamically.
"""

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass
from utils.logger import logger

@dataclass
class ToolDefinition:
    """Metadata for a tool that can be used by an agent."""
    name: str
    func: Callable
    description: str
    parameters: Dict[str, Any]  # JSON Schema-like description of arguments
    category: str = "general"

class ToolRegistry:
    """
    Central registry for agent tools. 
    Allows agents to discover and execute Python functions dynamically.
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        logger.info("ToolRegistry initialized. Ready for agentic tooling.")

    def register_tool(self, name: Optional[str] = None, category: str = "general"):
        """
        Decorator to register a function as a tool.
        Usage:
        @registry.register_tool(name="get_weather", category="utility")
        def get_weather(city: str): ...
        """
        def decorator(func: Callable):
            # Use the name provided in the decorator, or fall back to the function's name
            tool_name = name if name is not None else func.__name__
            
            # Extract parameters from function signature
            sig = inspect.signature(func)
            parameters = {}
            for p_name, param in sig.parameters.items():
                parameters[p_name] = {
                    "type": str(param.annotation.__name__) if param.annotation != inspect.Parameter.empty else "any",
                    "required": param.default == inspect.Parameter.empty
                }
            
            # Use docstring as tool description
            description = inspect.getdoc(func) or "No description provided."
            
            tool_def = ToolDefinition(
                name=tool_name,
                func=func,
                description=description,
                parameters=parameters,
                category=category
            )
            
            self._tools[tool_name] = tool_def
            logger.info(f"Tool Registered: {tool_name} | Category: {category}")
            return func
        
        return decorator

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Retrieve a tool definition by name."""
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[ToolDefinition]:
        """List all registered tools, optionally filtered by category."""
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Tuple[Any, bool]:
        """
        Executes a registered tool with the provided arguments.
        Returns (result, success_flag).
        """
        tool = self.get_tool(name)
        if not tool:
            logger.error(f"Tool Execution Failed: Tool {name} not found in registry.")
            return f"Error: Tool {name} not found.", False
        
        try:
            logger.info(f"Executing Tool: {name} with args: {args}")
            result = tool.func(**args)
            return result, True
        except Exception as e:
            logger.exception(f"Tool Execution Error: {name} failed with {str(e)}")
            return f"Error executing tool {name}: {str(e)}", False

# Global registry instance
registry = ToolRegistry()

"""
Tool registry for managing MCP tools.
"""

import logging
from typing import Dict, List, Optional, Protocol, Any

from mcp.types import Tool

logger = logging.getLogger(__name__)


class ToolHandler(Protocol):
    """Protocol for tool handlers."""
    
    def get_tool_definition(self) -> Tool:
        """Get the MCP tool definition."""
        ...
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        ...


class ToolRegistry:
    """Registry for managing MCP tools and their handlers."""
    
    def __init__(self) -> None:
        """Initialize the tool registry."""
        self._tools: Dict[str, Tool] = {}
        self._handlers: Dict[str, ToolHandler] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}
    
    def register_tool(self, handler: ToolHandler) -> None:
        """Register a tool handler."""
        tool_def = handler.get_tool_definition()
        tool_name = tool_def.name
        
        if tool_name in self._tools:
            logger.warning(f"Tool {tool_name} is already registered, overwriting")
        
        self._tools[tool_name] = tool_def
        self._handlers[tool_name] = handler
        
        # Store schema if available
        if hasattr(tool_def, 'inputSchema') and tool_def.inputSchema:
            self._schemas[tool_name] = tool_def.inputSchema
        
        logger.debug(f"Registered tool: {tool_name}")
    
    def get_tool_handler(self, tool_name: str) -> Optional[ToolHandler]:
        """Get a tool handler by name."""
        return self._handlers.get(tool_name)
    
    def get_tool_definition(self, tool_name: str) -> Optional[Tool]:
        """Get a tool definition by name."""
        return self._tools.get(tool_name)
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get a tool's input schema by name."""
        return self._schemas.get(tool_name)
    
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tool definitions."""
        return list(self._tools.values())
    
    def get_tool_names(self) -> List[str]:
        """Get all registered tool names."""
        return list(self._tools.keys())
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool by name."""
        if tool_name not in self._tools:
            return False
        
        del self._tools[tool_name]
        del self._handlers[tool_name]
        self._schemas.pop(tool_name, None)
        
        logger.debug(f"Unregistered tool: {tool_name}")
        return True
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._handlers.clear()
        self._schemas.clear()
        logger.debug("Cleared all registered tools")
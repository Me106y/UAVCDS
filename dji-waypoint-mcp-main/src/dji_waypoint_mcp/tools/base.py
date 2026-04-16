"""
Base classes for MCP tools.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from mcp.types import Tool
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """Standard result format for tool execution."""
    
    success: bool = True
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(
        cls, message: str = "Operation completed successfully", data: Optional[Dict[str, Any]] = None
    ) -> "ToolResult":
        """Create a success result."""
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error_result(cls, error: str, message: str = "Operation failed") -> "ToolResult":
        """Create an error result."""
        return cls(success=False, message=message, error=error)


class BaseTool(ABC):
    """Base class for all MCP tools."""
    
    def __init__(self) -> None:
        """Initialize the base tool."""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def get_tool_definition(self) -> Tool:
        """Get the MCP tool definition."""
        pass
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        pass
    
    def validate_arguments(
        self, arguments: Dict[str, Any], schema_class: Optional[type] = None
    ) -> Dict[str, Any]:
        """Validate tool arguments using Pydantic model."""
        if schema_class is None:
            return arguments
        
        try:
            validated = schema_class(**arguments)
            return validated.dict()
        except ValidationError as e:
            raise ValueError(f"Invalid arguments: {e}")
    
    def format_success_response(
        self, message: str = "Operation completed successfully", data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format a success response."""
        result = ToolResult.success_result(message, data)
        return result.dict()
    
    def format_error_response(
        self, error: str, message: str = "Operation failed"
    ) -> Dict[str, Any]:
        """Format an error response."""
        result = ToolResult.error_result(error, message)
        return result.dict()
    
    async def safe_execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Safely execute the tool with error handling."""
        try:
            self.logger.info(f"Executing tool: {self.__class__.__name__}")
            self.logger.debug(f"Arguments: {arguments}")
            
            result = await self.execute(arguments)
            
            self.logger.info(f"Tool execution completed: {self.__class__.__name__}")
            return result
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
            return self.format_error_response(str(e))


class ValidationMixin:
    """Mixin for common validation utilities."""
    
    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> None:
        """Validate latitude and longitude coordinates."""
        if not (-90 <= lat <= 90):
            raise ValueError(f"Invalid latitude: {lat}. Must be between -90 and 90.")
        if not (-180 <= lon <= 180):
            raise ValueError(f"Invalid longitude: {lon}. Must be between -180 and 180.")
    
    @staticmethod
    def validate_positive_number(value: float, name: str) -> None:
        """Validate that a number is positive."""
        if value <= 0:
            raise ValueError(f"{name} must be positive, got: {value}")
    
    @staticmethod
    def validate_range(value: float, min_val: float, max_val: float, name: str) -> None:
        """Validate that a value is within a specified range."""
        if not (min_val <= value <= max_val):
            raise ValueError(
                f"{name} must be between {min_val} and {max_val}, got: {value}"
            )
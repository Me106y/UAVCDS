"""
Unit tests for the MCP server.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from dji_waypoint_mcp.server import DJIWaypointMCPServer
from dji_waypoint_mcp.tools.registry import ToolRegistry


class TestDJIWaypointMCPServer:
    """Test cases for the DJI Waypoint MCP Server."""
    
    def test_server_initialization(self):
        """Test server initializes correctly."""
        server = DJIWaypointMCPServer()
        
        assert server.server is not None
        assert server.tool_registry is not None
        assert isinstance(server.tool_registry, ToolRegistry)
    
    def test_tool_registration(self):
        """Test that tools are registered during initialization."""
        server = DJIWaypointMCPServer()
        
        # Check that tools are registered
        tools = server.tool_registry.get_all_tools()
        assert len(tools) > 0
        
        # Check for expected tool names
        tool_names = server.tool_registry.get_tool_names()
        expected_tools = [
            "plan_waypoint_mission",
            "plan_mapping_mission", 
            "generate_kmz",
            "validate_flight_plan"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    def test_validate_tool_arguments(self):
        """Test tool argument validation."""
        server = DJIWaypointMCPServer()
        
        # Test with valid tool
        args = {"test": "value"}
        result = server._validate_tool_arguments("plan_waypoint_mission", args)
        assert result == args
        
        # Test with invalid tool
        with pytest.raises(ValueError, match="Unknown tool"):
            server._validate_tool_arguments("nonexistent_tool", args)
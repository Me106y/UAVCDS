"""
Main MCP server implementation for DJI Waypoint planning service.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence

import mcp.server
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

from .config import settings, setup_logging
from .tools.registry import ToolRegistry
from .tools.waypoint_planning import WaypointPlanningTool
from .tools.mapping_missions import MappingMissionTool
from .tools.oblique_missions import ObliqueMissionTool
from .tools.multi_flight_coordinator import MultiFlightCoordinator
from .tools.device_query import DeviceQueryTool
from .tools.route_optimizer import RouteOptimizer
from .tools.strip_missions import StripMissionTool
from .tools.utility_tools import UtilityTools
from .tools.kmz_generation import KMZGenerationTool
from .tools.validation import ValidationTool

logger = logging.getLogger(__name__)


class DJIWaypointMCPServer:
    """Main MCP server for DJI waypoint planning."""
    
    def __init__(self) -> None:
        """Initialize the MCP server."""
        self.server = Server("dji-waypoint-mcp")
        self.tool_registry = ToolRegistry()
        self._setup_handlers()
        self._register_tools()
    
    def _setup_handlers(self) -> None:
        """Setup MCP protocol handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """Handle list_tools request."""
            logger.debug("Handling list_tools request")
            tools = self.tool_registry.get_all_tools()
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Optional[Dict[str, Any]] = None
        ) -> CallToolResult:
            """Handle call_tool request."""
            logger.info(f"Handling call_tool request: {name}")
            logger.debug(f"Tool arguments: {arguments}")
            
            try:
                # Get the tool from registry
                tool_handler = self.tool_registry.get_tool_handler(name)
                if not tool_handler:
                    raise ValueError(f"Unknown tool: {name}")
                
                # Validate arguments
                validated_args = self._validate_tool_arguments(name, arguments or {})
                
                # Execute the tool
                result = await tool_handler.execute(validated_args)
                
                # Format the response
                payload_text = (
                    json.dumps(result, ensure_ascii=False)
                    if isinstance(result, dict)
                    else str(result)
                )
                is_error = False
                if isinstance(result, dict):
                    is_error = bool(result.get("error")) or (result.get("success") is False)
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=payload_text
                        )
                    ],
                    isError=is_error
                )
                
            except Exception as e:
                logger.error(f"Error executing tool {name}: {str(e)}", exc_info=True)
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", 
                            text=f"Error executing tool {name}: {str(e)}"
                        )
                    ],
                    isError=True
                )
    
    def _register_tools(self) -> None:
        """Register all available tools."""
        logger.info("Registering MCP tools")
        
        # Register waypoint planning tools
        waypoint_tool = WaypointPlanningTool()
        self.tool_registry.register_tool(waypoint_tool)
        
        # Register mapping mission tools
        mapping_tool = MappingMissionTool()
        self.tool_registry.register_tool(mapping_tool)
        
        # Register oblique mission tools
        oblique_tool = ObliqueMissionTool()
        self.tool_registry.register_tool(oblique_tool)
        
        # Register multi-flight coordinator
        coordinator_tool = MultiFlightCoordinator()
        self.tool_registry.register_tool(coordinator_tool)
        
        # Register device query tool
        device_query_tool = DeviceQueryTool()
        self.tool_registry.register_tool(device_query_tool)
        
        # Register route optimizer tool
        route_optimizer_tool = RouteOptimizer()
        self.tool_registry.register_tool(route_optimizer_tool)
        
        # Register strip mission tool
        strip_mission_tool = StripMissionTool()
        self.tool_registry.register_tool(strip_mission_tool)
        
        # Register utility tools
        utility_tools = UtilityTools()
        self.tool_registry.register_tool(utility_tools)
        
        # Register KMZ generation tools
        kmz_tool = KMZGenerationTool()
        self.tool_registry.register_tool(kmz_tool)
        
        # Register validation tools
        validation_tool = ValidationTool()
        self.tool_registry.register_tool(validation_tool)
        
        logger.info(f"Registered {len(self.tool_registry.get_all_tools())} tools")
    
    def _validate_tool_arguments(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate tool arguments against schema."""
        tool_handler = self.tool_registry.get_tool_handler(tool_name)
        if not tool_handler:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Get tool schema for validation
        tool_schema = self.tool_registry.get_tool_schema(tool_name)
        if not tool_schema:
            return arguments
        
        # Perform basic validation
        # TODO: Implement proper JSON schema validation
        return arguments
    
    async def run(self) -> None:
        """Run the MCP server."""
        logger.info("Starting DJI Waypoint MCP Server")
        logger.info(f"Server version: {settings.server_version}")
        
        # Create necessary directories
        settings.temp_dir.mkdir(parents=True, exist_ok=True)
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run the server
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=settings.server_name,
                    server_version=settings.server_version,
                    capabilities=self.server.get_capabilities(
                        notification_options=mcp.server.NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main() -> None:
    """Main entry point for the MCP server."""
    # Setup logging
    setup_logging()
    
    # Create and run server
    server = DJIWaypointMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())

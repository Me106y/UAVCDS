"""
Unit tests for waypoint planning tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from dji_waypoint_mcp.tools.waypoint_planning import WaypointPlanningTool, WaypointInput, WaypointMissionInput
from dji_waypoint_mcp.models import HeightMode, WaypointTurnMode


class TestWaypointPlanningTool:
    """Test cases for the waypoint planning tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = WaypointPlanningTool()
    
    def test_tool_definition(self):
        """Test tool definition is properly configured."""
        tool_def = self.tool.get_tool_definition()
        
        assert tool_def.name == "plan_waypoint_mission"
        assert "waypoint flight mission" in tool_def.description
        assert tool_def.inputSchema is not None
        assert "waypoints" in tool_def.inputSchema["properties"]
        assert tool_def.inputSchema["required"] == ["waypoints"]
    
    @pytest.mark.asyncio
    async def test_simple_waypoint_mission(self):
        """Test planning a simple waypoint mission."""
        arguments = {
            "waypoints": [
                {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                {"latitude": 40.7589, "longitude": -73.9851, "altitude": 120.0}
            ],
            "aircraft_type": "M30",
            "flight_speed": 5.0
        }
        
        result = await self.tool.execute(arguments)
        
        assert result["success"] is True
        assert "waypoints" in result["message"]
        assert result["data"]["flight_path"]["waypoint_count"] == 2
        assert result["data"]["configuration"]["aircraft_type"] == "M30"
        assert result["data"]["safety_validation"]["is_valid"] is True
    
    @pytest.mark.asyncio
    async def test_waypoint_mission_with_actions(self):
        """Test planning waypoint mission with actions."""
        arguments = {
            "waypoints": [
                {
                    "latitude": 40.7128, 
                    "longitude": -74.0060, 
                    "altitude": 100.0,
                    "actions": [
                        {"type": "takePhoto", "parameters": {"suffix": "point1"}}
                    ]
                },
                {"latitude": 40.7589, "longitude": -73.9851, "altitude": 120.0}
            ]
        }
        
        result = await self.tool.execute(arguments)
        
        assert result["success"] is True
        assert result["data"]["statistics"]["action_count"] == 1
    
    @pytest.mark.asyncio
    async def test_invalid_coordinates(self):
        """Test handling of invalid coordinates."""
        arguments = {
            "waypoints": [
                {"latitude": 91.0, "longitude": -74.0060, "altitude": 100.0},  # Invalid latitude
                {"latitude": 40.7589, "longitude": -73.9851, "altitude": 120.0}
            ]
        }
        
        result = await self.tool.execute(arguments)
        
        assert result["success"] is False
        assert "Invalid input parameters" in result["error"]
    
    @pytest.mark.asyncio
    async def test_insufficient_waypoints(self):
        """Test handling of insufficient waypoints."""
        arguments = {
            "waypoints": [
                {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0}
            ]
        }
        
        result = await self.tool.execute(arguments)
        
        assert result["success"] is False
        assert "Invalid input parameters" in result["error"]
    
    @pytest.mark.asyncio
    async def test_flight_safety_validation(self):
        """Test flight safety validation."""
        # Create waypoints that are very close together
        arguments = {
            "waypoints": [
                {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                {"latitude": 40.7128001, "longitude": -74.0060001, "altitude": 100.0}  # Very close
            ]
        }
        
        result = await self.tool.execute(arguments)
        
        assert result["success"] is True
        # Should have warnings about short distance
        assert len(result["data"]["safety_validation"]["warnings"]) > 0
    
    @pytest.mark.asyncio
    async def test_distance_calculation(self):
        """Test distance calculation between waypoints."""
        # Create waypoints with known distance (approximately 1km apart)
        arguments = {
            "waypoints": [
                {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                {"latitude": 40.7218, "longitude": -74.0060, "altitude": 100.0}  # ~1km north
            ]
        }
        
        result = await self.tool.execute(arguments)
        
        assert result["success"] is True
        # Distance should be approximately 1000m
        distance = result["data"]["statistics"]["total_distance"]
        assert 900 < distance < 1100  # Allow some tolerance
    
    @pytest.mark.asyncio
    async def test_flight_time_estimation(self):
        """Test flight time estimation."""
        arguments = {
            "waypoints": [
                {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                {"latitude": 40.7218, "longitude": -74.0060, "altitude": 100.0}
            ],
            "flight_speed": 10.0
        }
        
        result = await self.tool.execute(arguments)
        
        assert result["success"] is True
        
        distance = result["data"]["statistics"]["total_distance"]
        flight_time = result["data"]["statistics"]["estimated_flight_time"]
        expected_time = distance / 10.0
        
        assert abs(flight_time - expected_time) < 1.0  # Within 1 second tolerance
    
    def test_waypoint_input_validation(self):
        """Test waypoint input validation."""
        # Valid waypoint
        valid_wp = WaypointInput(
            latitude=40.7128,
            longitude=-74.0060,
            altitude=100.0
        )
        assert valid_wp.latitude == 40.7128
        
        # Invalid latitude
        with pytest.raises(Exception):
            WaypointInput(latitude=91.0, longitude=-74.0060, altitude=100.0)
        
        # Invalid longitude
        with pytest.raises(Exception):
            WaypointInput(latitude=40.7128, longitude=181.0, altitude=100.0)
    
    def test_mission_input_validation(self):
        """Test mission input validation."""
        waypoints = [
            WaypointInput(latitude=40.7128, longitude=-74.0060, altitude=100.0),
            WaypointInput(latitude=40.7589, longitude=-73.9851, altitude=120.0)
        ]
        
        # Valid mission
        mission = WaypointMissionInput(waypoints=waypoints)
        assert len(mission.waypoints) == 2
        assert mission.flight_speed == 5.0
        assert mission.height_mode == "EGM96"
        
        # Invalid - insufficient waypoints
        with pytest.raises(Exception):
            WaypointMissionInput(waypoints=[waypoints[0]])
    
    def test_action_group_creation(self):
        """Test action group creation."""
        actions_data = [
            {"type": "takePhoto", "parameters": {"suffix": "test"}},
            {"type": "hover", "parameters": {"time": 5.0}}
        ]
        
        action_groups = self.tool._create_action_groups(actions_data, 0)
        
        assert len(action_groups) == 1
        assert len(action_groups[0].actions) == 2
        assert action_groups[0].start_index == 0
        assert action_groups[0].end_index == 0
    
    def test_distance_calculation_method(self):
        """Test the distance calculation method directly."""
        from dji_waypoint_mcp.models import Waypoint, Coordinates
        
        # Create two waypoints 1 degree apart (approximately 111km)
        wp1 = Waypoint(
            index=0,
            coordinates=Coordinates(latitude=0.0, longitude=0.0, altitude=100.0)
        )
        wp2 = Waypoint(
            index=1,
            coordinates=Coordinates(latitude=1.0, longitude=0.0, altitude=100.0)
        )
        
        distance = self.tool._calculate_distance_between_waypoints(wp1, wp2)
        
        # Should be approximately 111km (111,000m)
        assert 110000 < distance < 112000
    
    def test_bounding_box_conversion(self):
        """Test bounding box conversion to dictionary."""
        from dji_waypoint_mcp.models import BoundingBox
        
        bbox = BoundingBox(
            min_latitude=40.0,
            max_latitude=41.0,
            min_longitude=-75.0,
            max_longitude=-74.0
        )
        
        bbox_dict = self.tool._get_bounding_box_dict(bbox)
        
        assert bbox_dict["min_latitude"] == 40.0
        assert bbox_dict["max_latitude"] == 41.0
        assert bbox_dict["min_longitude"] == -75.0
        assert bbox_dict["max_longitude"] == -74.0
        
        # Test with None
        assert self.tool._get_bounding_box_dict(None) is None
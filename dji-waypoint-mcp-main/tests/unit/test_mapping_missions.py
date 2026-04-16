"""
Unit tests for mapping mission tools.
"""

import pytest
import math
from unittest.mock import patch, MagicMock
from shapely.geometry import Polygon, LineString

from dji_waypoint_mcp.tools.mapping_missions import (
    MappingMissionTool, 
    FlightLineGenerator, 
    MappingMissionInput, 
    SurveyAreaPoint
)
from dji_waypoint_mcp.models import Coordinates, ActionType


class TestSurveyAreaPoint:
    """Test cases for SurveyAreaPoint model."""
    
    def test_valid_survey_point(self):
        """Test valid survey area point creation."""
        point = SurveyAreaPoint(latitude=40.7128, longitude=-74.0060)
        assert point.latitude == 40.7128
        assert point.longitude == -74.0060
    
    def test_invalid_latitude(self):
        """Test invalid latitude validation."""
        with pytest.raises(Exception):
            SurveyAreaPoint(latitude=91.0, longitude=-74.0060)
        
        with pytest.raises(Exception):
            SurveyAreaPoint(latitude=-91.0, longitude=-74.0060)
    
    def test_invalid_longitude(self):
        """Test invalid longitude validation."""
        with pytest.raises(Exception):
            SurveyAreaPoint(latitude=40.7128, longitude=181.0)
        
        with pytest.raises(Exception):
            SurveyAreaPoint(latitude=40.7128, longitude=-181.0)


class TestMappingMissionInput:
    """Test cases for MappingMissionInput model."""
    
    def test_valid_mapping_input(self):
        """Test valid mapping mission input."""
        survey_area = [
            SurveyAreaPoint(latitude=40.7128, longitude=-74.0060),
            SurveyAreaPoint(latitude=40.7228, longitude=-74.0060),
            SurveyAreaPoint(latitude=40.7228, longitude=-73.9960),
            SurveyAreaPoint(latitude=40.7128, longitude=-73.9960)
        ]
        
        mission_input = MappingMissionInput(
            survey_area=survey_area,
            flight_height=120.0,
            overlap_rate=85.0,
            sidelap_rate=75.0
        )
        
        assert len(mission_input.survey_area) == 4
        assert mission_input.flight_height == 120.0
        assert mission_input.overlap_rate == 85.0
        assert mission_input.sidelap_rate == 75.0
    
    def test_default_values(self):
        """Test default values in mapping input."""
        survey_area = [
            SurveyAreaPoint(latitude=40.7128, longitude=-74.0060),
            SurveyAreaPoint(latitude=40.7228, longitude=-74.0060),
            SurveyAreaPoint(latitude=40.7228, longitude=-73.9960)
        ]
        
        mission_input = MappingMissionInput(survey_area=survey_area)
        
        assert mission_input.flight_height == 100.0
        assert mission_input.overlap_rate == 80.0
        assert mission_input.sidelap_rate == 70.0
        assert mission_input.flight_direction == 0.0
        assert mission_input.flight_speed == 5.0
        assert mission_input.aircraft_type == "M30"
        assert mission_input.margin == 20.0
        assert mission_input.shoot_mode == "time"
        assert mission_input.gimbal_pitch == -90.0
        assert mission_input.enable_terrain_following is False
    
    def test_insufficient_survey_points(self):
        """Test validation with insufficient survey points."""
        survey_area = [
            SurveyAreaPoint(latitude=40.7128, longitude=-74.0060),
            SurveyAreaPoint(latitude=40.7228, longitude=-74.0060)
        ]
        
        with pytest.raises(Exception):
            MappingMissionInput(survey_area=survey_area)
    
    def test_parameter_ranges(self):
        """Test parameter range validation."""
        survey_area = [
            SurveyAreaPoint(latitude=40.7128, longitude=-74.0060),
            SurveyAreaPoint(latitude=40.7228, longitude=-74.0060),
            SurveyAreaPoint(latitude=40.7228, longitude=-73.9960)
        ]
        
        # Test flight height range
        with pytest.raises(Exception):
            MappingMissionInput(survey_area=survey_area, flight_height=5.0)  # Too low
        
        with pytest.raises(Exception):
            MappingMissionInput(survey_area=survey_area, flight_height=2000.0)  # Too high
        
        # Test overlap rate range
        with pytest.raises(Exception):
            MappingMissionInput(survey_area=survey_area, overlap_rate=40.0)  # Too low
        
        with pytest.raises(Exception):
            MappingMissionInput(survey_area=survey_area, overlap_rate=98.0)  # Too high


class TestFlightLineGenerator:
    """Test cases for flight line generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = FlightLineGenerator()
        
        # Create a simple square polygon for testing
        self.test_polygon = Polygon([
            (-74.0060, 40.7128),  # SW corner
            (-74.0060, 40.7228),  # NW corner
            (-73.9960, 40.7228),  # NE corner
            (-73.9960, 40.7128),  # SE corner
            (-74.0060, 40.7128)   # Close polygon
        ])
    
    def test_line_spacing_calculation(self):
        """Test line spacing calculation."""
        camera_specs = {
            "sensor_width": 23.5,
            "sensor_height": 15.6,
            "focal_length": 24.0,
            "image_width": 5472,
            "image_height": 3648
        }
        
        line_spacing = self.generator.calculate_line_spacing(
            flight_height=100.0,
            camera_specs=camera_specs,
            sidelap_percentage=70.0
        )
        
        assert line_spacing > 0
        assert isinstance(line_spacing, float)
        
        # Higher sidelap should result in smaller line spacing
        smaller_spacing = self.generator.calculate_line_spacing(
            flight_height=100.0,
            camera_specs=camera_specs,
            sidelap_percentage=80.0
        )
        
        assert smaller_spacing < line_spacing
    
    def test_photo_interval_calculation(self):
        """Test photo interval calculation."""
        camera_specs = {
            "sensor_width": 23.5,
            "sensor_height": 15.6,
            "focal_length": 24.0
        }
        
        photo_interval = self.generator.calculate_photo_interval(
            flight_speed=5.0,
            flight_height=100.0,
            camera_specs=camera_specs,
            overlap_percentage=80.0
        )
        
        assert photo_interval >= 1.0  # Minimum 1 second
        assert isinstance(photo_interval, float)
        
        # Higher overlap should result in shorter interval
        shorter_interval = self.generator.calculate_photo_interval(
            flight_speed=5.0,
            flight_height=100.0,
            camera_specs=camera_specs,
            overlap_percentage=90.0
        )
        
        assert shorter_interval <= photo_interval
    
    def test_flight_line_generation(self):
        """Test flight line generation."""
        flight_lines = self.generator.generate_flight_lines(
            survey_polygon=self.test_polygon,
            flight_direction=0.0,  # North-South
            line_spacing=50.0,     # 50 meters
            margin=10.0
        )
        
        assert len(flight_lines) > 0
        assert all(isinstance(line, LineString) for line in flight_lines)
        
        # Check that lines intersect with the polygon
        for line in flight_lines:
            intersection = line.intersection(self.test_polygon)
            assert not intersection.is_empty
    
    def test_flight_line_optimization(self):
        """Test flight line order optimization (boustrophedon pattern)."""
        # Create some test lines
        test_lines = [
            LineString([(-74.0050, 40.7130), (-74.0050, 40.7220)]),
            LineString([(-74.0040, 40.7130), (-74.0040, 40.7220)]),
            LineString([(-74.0030, 40.7130), (-74.0030, 40.7220)])
        ]
        
        optimized_lines = self.generator._optimize_flight_line_order(test_lines)
        
        assert len(optimized_lines) == len(test_lines)
        assert all(isinstance(line, LineString) for line in optimized_lines)
        
        # First line should be the leftmost
        first_line_x = optimized_lines[0].coords[0][0]
        assert first_line_x == min(line.coords[0][0] for line in test_lines)
    
    def test_empty_flight_lines(self):
        """Test handling of empty flight lines."""
        optimized = self.generator._optimize_flight_line_order([])
        assert optimized == []
    
    def test_different_flight_directions(self):
        """Test flight line generation with different directions."""
        # North-South (0 degrees)
        lines_ns = self.generator.generate_flight_lines(
            self.test_polygon, 0.0, 50.0
        )
        
        # East-West (90 degrees)
        lines_ew = self.generator.generate_flight_lines(
            self.test_polygon, 90.0, 50.0
        )
        
        assert len(lines_ns) > 0
        assert len(lines_ew) > 0
        
        # Lines should be different for different directions
        # (This is a basic check - in practice, the exact comparison would be more complex)
        assert len(lines_ns) != len(lines_ew) or lines_ns[0].coords != lines_ew[0].coords


class TestMappingMissionTool:
    """Test cases for mapping mission tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = MappingMissionTool()
    
    def test_tool_definition(self):
        """Test tool definition is properly configured."""
        tool_def = self.tool.get_tool_definition()
        
        assert tool_def.name == "plan_mapping_mission"
        assert "automated mapping survey mission" in tool_def.description
        assert tool_def.inputSchema is not None
        assert "survey_area" in tool_def.inputSchema["properties"]
        assert tool_def.inputSchema["required"] == ["survey_area"]
    
    @pytest.mark.asyncio
    async def test_successful_mapping_mission(self):
        """Test successful mapping mission planning."""
        arguments = {
            "survey_area": [
                {"latitude": 40.7128, "longitude": -74.0060},
                {"latitude": 40.7228, "longitude": -74.0060},
                {"latitude": 40.7228, "longitude": -73.9960},
                {"latitude": 40.7128, "longitude": -73.9960}
            ],
            "flight_height": 120.0,
            "overlap_rate": 85.0,
            "sidelap_rate": 75.0,
            "flight_direction": 45.0,
            "aircraft_type": "M30"
        }
        
        result = await self.tool.execute(arguments)
        
        assert result["success"] is True
        assert "flight lines" in result["message"]
        assert result["data"]["flight_path"]["waypoint_count"] > 0
        assert result["data"]["flight_path"]["flight_lines"] > 0
        assert result["data"]["survey_configuration"]["area_hectares"] > 0
        assert result["data"]["photo_configuration"]["estimated_photos"] > 0
    
    @pytest.mark.asyncio
    async def test_invalid_survey_area(self):
        """Test handling of invalid survey area."""
        arguments = {
            "survey_area": [
                {"latitude": 40.7128, "longitude": -74.0060},
                {"latitude": 40.7228, "longitude": -74.0060}
                # Only 2 points - insufficient for polygon
            ]
        }
        
        result = await self.tool.execute(arguments)
        
        assert result["success"] is False
        assert "Invalid input parameters" in result["error"]
    
    @pytest.mark.asyncio
    async def test_different_aircraft_types(self):
        """Test mapping mission with different aircraft types."""
        base_arguments = {
            "survey_area": [
                {"latitude": 40.7128, "longitude": -74.0060},
                {"latitude": 40.7228, "longitude": -74.0060},
                {"latitude": 40.7228, "longitude": -73.9960},
                {"latitude": 40.7128, "longitude": -73.9960}
            ]
        }
        
        # Test M30
        args_m30 = {**base_arguments, "aircraft_type": "M30"}
        result_m30 = await self.tool.execute(args_m30)
        assert result_m30["success"] is True
        
        # Test M3E
        args_m3e = {**base_arguments, "aircraft_type": "M3E"}
        result_m3e = await self.tool.execute(args_m3e)
        assert result_m3e["success"] is True
        
        # Results should be different due to different camera specs
        assert (result_m30["data"]["photo_configuration"]["ground_resolution"] != 
                result_m3e["data"]["photo_configuration"]["ground_resolution"])
    
    @pytest.mark.asyncio
    async def test_margin_application(self):
        """Test survey area margin application."""
        base_arguments = {
            "survey_area": [
                {"latitude": 40.7128, "longitude": -74.0060},
                {"latitude": 40.7228, "longitude": -74.0060},
                {"latitude": 40.7228, "longitude": -73.9960},
                {"latitude": 40.7128, "longitude": -73.9960}
            ]
        }
        
        # Test without margin
        args_no_margin = {**base_arguments, "margin": 0.0}
        result_no_margin = await self.tool.execute(args_no_margin)
        
        # Test with margin
        args_with_margin = {**base_arguments, "margin": 50.0}
        result_with_margin = await self.tool.execute(args_with_margin)
        
        assert result_no_margin["success"] is True
        assert result_with_margin["success"] is True
        
        # With margin should have more waypoints/longer distance
        assert (result_with_margin["data"]["flight_path"]["total_distance"] >= 
                result_no_margin["data"]["flight_path"]["total_distance"])
    
    def test_survey_polygon_creation(self):
        """Test survey polygon creation."""
        survey_points = [
            SurveyAreaPoint(latitude=40.7128, longitude=-74.0060),
            SurveyAreaPoint(latitude=40.7228, longitude=-74.0060),
            SurveyAreaPoint(latitude=40.7228, longitude=-73.9960),
            SurveyAreaPoint(latitude=40.7128, longitude=-73.9960)
        ]
        
        polygon = self.tool._create_survey_polygon(survey_points)
        
        assert isinstance(polygon, Polygon)
        assert polygon.is_valid
        assert len(polygon.exterior.coords) == 5  # 4 points + closing point
    
    def test_camera_specs_retrieval(self):
        """Test camera specifications retrieval."""
        # Test known aircraft
        m30_specs = self.tool._get_camera_specs("M30")
        assert "sensor_width" in m30_specs
        assert "focal_length" in m30_specs
        assert m30_specs["sensor_width"] > 0
        
        m3e_specs = self.tool._get_camera_specs("M3E")
        assert "sensor_width" in m3e_specs
        assert m3e_specs["sensor_width"] != m30_specs["sensor_width"]
        
        # Test unknown aircraft (should default to M30)
        unknown_specs = self.tool._get_camera_specs("UNKNOWN")
        assert unknown_specs == m30_specs
    
    def test_flight_lines_to_waypoints(self):
        """Test conversion of flight lines to waypoints."""
        # Create test flight lines
        flight_lines = [
            LineString([(-74.0050, 40.7130), (-74.0050, 40.7220)]),
            LineString([(-74.0040, 40.7220), (-74.0040, 40.7130)])  # Reversed for boustrophedon
        ]
        
        waypoints = self.tool._flight_lines_to_waypoints(
            flight_lines, 
            flight_height=100.0, 
            flight_speed=5.0
        )
        
        assert len(waypoints) == 4  # 2 waypoints per line
        assert all(wp.coordinates.altitude == 100.0 for wp in waypoints)
        assert all(wp.speed == 5.0 for wp in waypoints)
        assert all(wp.index == i for i, wp in enumerate(waypoints))
    
    def test_photo_actions_addition(self):
        """Test addition of photo actions to waypoints."""
        # Create test waypoints
        waypoints = [
            self.tool._create_test_waypoint(0, 40.7128, -74.0060, 100.0),
            self.tool._create_test_waypoint(1, 40.7228, -74.0060, 100.0),
            self.tool._create_test_waypoint(2, 40.7228, -73.9960, 100.0),
            self.tool._create_test_waypoint(3, 40.7128, -73.9960, 100.0)
        ]
        
        mission_input = MappingMissionInput(
            survey_area=[
                SurveyAreaPoint(latitude=40.7128, longitude=-74.0060),
                SurveyAreaPoint(latitude=40.7228, longitude=-74.0060),
                SurveyAreaPoint(latitude=40.7228, longitude=-73.9960)
            ],
            shoot_mode="time",
            flight_speed=5.0,
            flight_height=100.0,
            overlap_rate=80.0
        )
        
        camera_specs = self.tool._get_camera_specs("M30")
        
        waypoints_with_actions = self.tool._add_photo_actions(
            waypoints, mission_input, camera_specs
        )
        
        # Check that some waypoints have actions
        waypoints_with_actions_count = sum(
            1 for wp in waypoints_with_actions if wp.action_groups
        )
        assert waypoints_with_actions_count > 0
        
        # Check action properties
        for wp in waypoints_with_actions:
            if wp.action_groups:
                action_group = wp.action_groups[0]
                assert len(action_group.actions) > 0
                assert action_group.actions[0].action_type == ActionType.TAKE_PHOTO
    
    def _create_test_waypoint(self, index: int, lat: float, lon: float, alt: float):
        """Helper method to create test waypoints."""
        from dji_waypoint_mcp.models import Waypoint, Coordinates
        
        return Waypoint(
            index=index,
            coordinates=Coordinates(latitude=lat, longitude=lon, altitude=alt),
            use_global_height=True,
            use_global_speed=True
        )
    
    def test_distance_calculation(self):
        """Test distance calculation between coordinates."""
        coord1 = Coordinates(latitude=40.7128, longitude=-74.0060)
        coord2 = Coordinates(latitude=40.7228, longitude=-74.0060)  # ~1.1km north
        
        distance = self.tool._calculate_distance(coord1, coord2)
        
        assert 1000 < distance < 1200  # Should be approximately 1.1km
        assert isinstance(distance, float)
    
    @pytest.mark.asyncio
    async def test_mission_statistics_calculation(self):
        """Test mission statistics calculation."""
        arguments = {
            "survey_area": [
                {"latitude": 40.7128, "longitude": -74.0060},
                {"latitude": 40.7228, "longitude": -74.0060},
                {"latitude": 40.7228, "longitude": -73.9960},
                {"latitude": 40.7128, "longitude": -73.9960}
            ],
            "flight_height": 100.0,
            "flight_speed": 8.0,
            "overlap_rate": 80.0
        }
        
        result = await self.tool.execute(arguments)
        
        assert result["success"] is True
        
        stats = result["data"]["statistics"]
        assert "survey_area_hectares" in stats
        assert "total_distance" in stats
        assert "estimated_flight_time" in stats
        assert "photo_interval" in stats
        assert "estimated_photos" in stats
        assert "ground_resolution" in stats
        
        # Verify reasonable values
        assert stats["survey_area_hectares"] > 0
        assert stats["total_distance"] > 0
        assert stats["estimated_flight_time"] > 0
        assert stats["photo_interval"] >= 1.0
        assert stats["estimated_photos"] >= 0
        assert stats["ground_resolution"] > 0


class TestMappingMissionIntegration:
    """Integration tests for mapping mission functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = MappingMissionTool()
    
    @pytest.mark.asyncio
    async def test_complete_mapping_workflow(self):
        """Test complete mapping mission workflow."""
        # Define a realistic survey area (small park in NYC)
        arguments = {
            "survey_area": [
                {"latitude": 40.7829, "longitude": -73.9654},  # Central Park corner
                {"latitude": 40.7839, "longitude": -73.9654},
                {"latitude": 40.7839, "longitude": -73.9644},
                {"latitude": 40.7829, "longitude": -73.9644}
            ],
            "flight_height": 80.0,
            "overlap_rate": 85.0,
            "sidelap_rate": 75.0,
            "flight_direction": 30.0,
            "flight_speed": 6.0,
            "aircraft_type": "M30T",
            "margin": 15.0,
            "shoot_mode": "time",
            "gimbal_pitch": -85.0
        }
        
        result = await self.tool.execute(arguments)
        
        # Verify successful execution
        assert result["success"] is True
        assert "flight lines" in result["message"]
        
        # Verify flight path data
        flight_path = result["data"]["flight_path"]
        assert flight_path["waypoint_count"] >= 4  # At least 2 flight lines
        assert flight_path["flight_lines"] >= 2
        assert flight_path["total_distance"] > 0
        assert flight_path["estimated_flight_time"] > 0
        
        # Verify survey configuration
        survey_config = result["data"]["survey_configuration"]
        assert survey_config["area_hectares"] > 0
        assert survey_config["flight_height"] == 80.0
        assert survey_config["overlap_rate"] == 85.0
        assert survey_config["sidelap_rate"] == 75.0
        assert survey_config["flight_direction"] == 30.0
        assert survey_config["line_spacing"] > 0
        
        # Verify photo configuration
        photo_config = result["data"]["photo_configuration"]
        assert photo_config["shoot_mode"] == "time"
        assert photo_config["photo_interval"] >= 1.0
        assert photo_config["estimated_photos"] > 0
        assert photo_config["ground_resolution"] > 0
        
        # Verify statistics are reasonable
        stats = result["data"]["statistics"]
        assert 0.1 < stats["survey_area_hectares"] < 10  # Reasonable area
        assert 100 < stats["total_distance"] < 10000  # Reasonable distance
        assert 10 < stats["estimated_flight_time"] < 3600  # 10 sec to 1 hour
        assert stats["estimated_photos"] > 0
    
    @pytest.mark.asyncio
    async def test_edge_case_handling(self):
        """Test handling of edge cases."""
        # Very small survey area
        small_area_args = {
            "survey_area": [
                {"latitude": 40.7128, "longitude": -74.0060},
                {"latitude": 40.7129, "longitude": -74.0060},
                {"latitude": 40.7129, "longitude": -74.0059}
            ]
        }
        
        result = await self.tool.execute(small_area_args)
        # Should still work, even if it generates minimal flight lines
        assert result["success"] is True or "failed" in result.get("error", "")
        
        # Very high overlap rates
        high_overlap_args = {
            "survey_area": [
                {"latitude": 40.7128, "longitude": -74.0060},
                {"latitude": 40.7228, "longitude": -74.0060},
                {"latitude": 40.7228, "longitude": -73.9960},
                {"latitude": 40.7128, "longitude": -73.9960}
            ],
            "overlap_rate": 95.0,
            "sidelap_rate": 90.0
        }
        
        result = await self.tool.execute(high_overlap_args)
        assert result["success"] is True
        
        # Should result in very short photo intervals and close line spacing
        if result["success"]:
            assert result["data"]["photo_configuration"]["photo_interval"] <= 2.0
            assert result["data"]["survey_configuration"]["line_spacing"] < 50.0
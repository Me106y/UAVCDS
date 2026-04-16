"""
Unit tests for KMZ generation tools.
"""

import pytest
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from xml.etree.ElementTree import fromstring

from dji_waypoint_mcp.tools.kmz_generation import KMZGenerationTool, WPMLGenerator, KMZGenerationInput
from dji_waypoint_mcp.models import (
    FlightPlan, FlightPath, MissionConfig, AircraftSpecs, PayloadSpecs,
    Waypoint, Coordinates, AircraftModel, PayloadModel, HeightMode
)


class TestWPMLGenerator:
    """Test cases for WPML XML generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = WPMLGenerator()
        
        # Create test flight plan and path
        aircraft = AircraftSpecs(
            model=AircraftModel.M30,
            enum_value=67,
            max_flight_speed=15.0,
            max_flight_height=500.0,
            max_flight_distance=50000.0,
            battery_life=45.0
        )
        
        payload = PayloadSpecs(
            model=PayloadModel.M30_DUAL_CAMERA,
            enum_value=52
        )
        
        mission_config = MissionConfig(aircraft=aircraft, payload=payload)
        
        self.flight_plan = FlightPlan(
            mission_config=mission_config,
            author="Test Author",
            create_time=1640995200000,  # Fixed timestamp for testing
            update_time=1640995200000
        )
        
        # Create test waypoints
        waypoints = [
            Waypoint(
                index=0,
                coordinates=Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
            ),
            Waypoint(
                index=1,
                coordinates=Coordinates(latitude=40.7228, longitude=-74.0160, altitude=120.0)
            )
        ]
        
        self.flight_path = FlightPath(
            waypoints=waypoints,
            global_speed=5.0,
            height_mode=HeightMode.EGM96
        )
    
    def test_generate_template_kml(self):
        """Test template.kml generation."""
        template_content = self.generator.generate_template_kml(self.flight_plan, self.flight_path)
        
        assert template_content is not None
        assert isinstance(template_content, str)
        assert 'xmlns="http://www.opengis.net/kml/2.2"' in template_content
        assert 'xmlns:wpml="http://www.dji.com/wpmz/1.0.2"' in template_content
        assert '<wpml:author>Test Author</wpml:author>' in template_content
        assert '<wpml:templateType>waypoint</wpml:templateType>' in template_content
        
        # Parse XML to ensure it's valid
        root = fromstring(template_content)
        assert root.tag == 'kml'
    
    def test_generate_waylines_wpml(self):
        """Test waylines.wpml generation."""
        waylines_content = self.generator.generate_waylines_wpml(self.flight_plan, self.flight_path)
        
        assert waylines_content is not None
        assert isinstance(waylines_content, str)
        assert 'xmlns="http://www.opengis.net/kml/2.2"' in waylines_content
        assert 'xmlns:wpml="http://www.dji.com/wpmz/1.0.2"' in waylines_content
        assert '<wpml:executeHeightMode>EGM96</wpml:executeHeightMode>' in waylines_content
        
        # Parse XML to ensure it's valid
        root = fromstring(waylines_content)
        assert root.tag == 'kml'
    
    def test_mission_config_generation(self):
        """Test mission configuration XML generation."""
        template_content = self.generator.generate_template_kml(self.flight_plan, self.flight_path)
        
        # Check for mission config elements
        assert '<wpml:missionConfig>' in template_content
        assert '<wpml:flyToWaylineMode>safely</wpml:flyToWaylineMode>' in template_content
        assert '<wpml:finishAction>goHome</wpml:finishAction>' in template_content
        assert '<wpml:droneEnumValue>67</wpml:droneEnumValue>' in template_content
        assert '<wpml:payloadEnumValue>52</wpml:payloadEnumValue>' in template_content
    
    def test_waypoint_generation(self):
        """Test waypoint XML generation."""
        template_content = self.generator.generate_template_kml(self.flight_plan, self.flight_path)
        
        # Check for waypoint elements
        assert '<Placemark>' in template_content
        assert '<Point>' in template_content
        assert '<coordinates>' in template_content
        assert '-74.006,40.7128,100.0' in template_content  # First waypoint coordinates
        assert '<wpml:index>0</wpml:index>' in template_content
        assert '<wpml:index>1</wpml:index>' in template_content
    
    def test_coordinate_formatting(self):
        """Test coordinate formatting in KML."""
        waypoint = self.flight_path.waypoints[0]
        kml_coords = waypoint.coordinates.to_kml_coordinates()
        
        assert kml_coords == "-74.006,40.7128,100.0"
        
        # Test without altitude
        coords_no_alt = Coordinates(latitude=40.7128, longitude=-74.0060)
        kml_coords_no_alt = coords_no_alt.to_kml_coordinates()
        assert kml_coords_no_alt == "-74.006,40.7128"
    
    def test_xml_prettification(self):
        """Test XML prettification."""
        from xml.etree.ElementTree import Element, SubElement
        
        root = Element('test')
        child = SubElement(root, 'child')
        child.text = 'content'
        
        prettified = self.generator._prettify_xml(root)
        
        assert isinstance(prettified, str)
        assert '<?xml version="1.0" encoding="utf-8"?>' in prettified
        assert '<test>' in prettified
        assert '<child>content</child>' in prettified


class TestKMZGenerationTool:
    """Test cases for KMZ generation tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = KMZGenerationTool()
    
    def test_tool_definition(self):
        """Test tool definition is properly configured."""
        tool_def = self.tool.get_tool_definition()
        
        assert tool_def.name == "generate_kmz"
        assert "WPML-compliant KMZ file" in tool_def.description
        assert tool_def.inputSchema is not None
        assert "flight_plan" in tool_def.inputSchema["properties"]
        assert tool_def.inputSchema["required"] == ["flight_plan"]
    
    @pytest.mark.asyncio
    async def test_kmz_generation_success(self):
        """Test successful KMZ file generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock settings to use temp directory
            with patch('dji_waypoint_mcp.tools.kmz_generation.settings') as mock_settings:
                mock_settings.output_dir = Path(temp_dir)
                
                arguments = {
                    "flight_plan": {
                        "waypoints": [
                            {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                            {"latitude": 40.7228, "longitude": -74.0160, "altitude": 120.0}
                        ],
                        "flight_speed": 5.0
                    },
                    "output_filename": "test_mission.kmz",
                    "include_template": True,
                    "author": "Test User"
                }
                
                result = await self.tool.execute(arguments)
                
                assert result["success"] is True
                assert "test_mission.kmz" in result["message"]
                assert result["data"]["waypoint_count"] == 2
                assert result["data"]["includes_template"] is True
                
                # Check that file was actually created
                output_path = Path(temp_dir) / "test_mission.kmz"
                assert output_path.exists()
                
                # Check KMZ file contents
                with zipfile.ZipFile(output_path, 'r') as kmz_file:
                    file_list = kmz_file.namelist()
                    assert 'waylines.wpml' in file_list
                    assert 'template.kml' in file_list
    
    @pytest.mark.asyncio
    async def test_kmz_generation_without_template(self):
        """Test KMZ generation without template file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('dji_waypoint_mcp.tools.kmz_generation.settings') as mock_settings:
                mock_settings.output_dir = Path(temp_dir)
                
                arguments = {
                    "flight_plan": {
                        "waypoints": [
                            {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                            {"latitude": 40.7228, "longitude": -74.0160, "altitude": 120.0}
                        ]
                    },
                    "include_template": False
                }
                
                result = await self.tool.execute(arguments)
                
                assert result["success"] is True
                assert result["data"]["includes_template"] is False
                
                # Check KMZ file contents
                output_path = Path(temp_dir) / "mission.kmz"
                with zipfile.ZipFile(output_path, 'r') as kmz_file:
                    file_list = kmz_file.namelist()
                    assert 'waylines.wpml' in file_list
                    assert 'template.kml' not in file_list
    
    @pytest.mark.asyncio
    async def test_kmz_generation_with_resources(self):
        """Test KMZ generation with resource directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('dji_waypoint_mcp.tools.kmz_generation.settings') as mock_settings:
                mock_settings.output_dir = Path(temp_dir)
                
                arguments = {
                    "flight_plan": {
                        "waypoints": [
                            {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                            {"latitude": 40.7228, "longitude": -74.0160, "altitude": 120.0}
                        ]
                    },
                    "include_resources": True
                }
                
                result = await self.tool.execute(arguments)
                
                assert result["success"] is True
                assert result["data"]["includes_resources"] is True
                
                # Check KMZ file contents
                output_path = Path(temp_dir) / "mission.kmz"
                with zipfile.ZipFile(output_path, 'r') as kmz_file:
                    file_list = kmz_file.namelist()
                    assert 'res/' in file_list
    
    @pytest.mark.asyncio
    async def test_invalid_flight_plan(self):
        """Test handling of invalid flight plan data."""
        arguments = {
            "flight_plan": {
                "waypoints": []  # Empty waypoints should cause error
            }
        }
        
        result = await self.tool.execute(arguments)
        
        assert result["success"] is False
        assert "Invalid input parameters" in result["error"] or "failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_file_statistics(self):
        """Test file statistics calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('dji_waypoint_mcp.tools.kmz_generation.settings') as mock_settings:
                mock_settings.output_dir = Path(temp_dir)
                
                arguments = {
                    "flight_plan": {
                        "waypoints": [
                            {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                            {"latitude": 40.7228, "longitude": -74.0160, "altitude": 120.0}
                        ]
                    }
                }
                
                result = await self.tool.execute(arguments)
                
                assert result["success"] is True
                assert "file_size" in result["data"]
                assert "file_size_bytes" in result["data"]
                assert "generation_time" in result["data"]
                assert result["data"]["file_size_bytes"] > 0
    
    def test_flight_object_creation(self):
        """Test creation of flight objects from input data."""
        flight_plan_data = {
            "waypoints": [
                {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                {"latitude": 40.7228, "longitude": -74.0160, "altitude": 120.0}
            ],
            "flight_speed": 8.0
        }
        
        flight_plan, flight_path = self.tool._create_flight_objects(flight_plan_data, "Test Author")
        
        assert flight_plan.author == "Test Author"
        assert flight_plan.mission_config.aircraft.model == AircraftModel.M30
        assert len(flight_path.waypoints) == 2
        assert flight_path.global_speed == 8.0
        assert flight_path.waypoints[0].coordinates.latitude == 40.7128
        assert flight_path.waypoints[1].coordinates.latitude == 40.7228
    
    def test_file_statistics_calculation(self):
        """Test file statistics calculation method."""
        with tempfile.NamedTemporaryFile(suffix='.kmz', delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_path = Path(temp_file.name)
        
        try:
            stats = self.tool._get_file_statistics(temp_path)
            
            assert "size" in stats
            assert "size_bytes" in stats
            assert "generation_time" in stats
            assert stats["size_bytes"] > 0
            assert "B" in stats["size"] or "KB" in stats["size"] or "MB" in stats["size"]
        finally:
            temp_path.unlink()
        
        # Test with non-existent file
        non_existent = Path("/non/existent/file.kmz")
        stats = self.tool._get_file_statistics(non_existent)
        assert stats["size"] == "0 B"
        assert stats["size_bytes"] == 0


class TestKMZGenerationInput:
    """Test cases for KMZ generation input validation."""
    
    def test_valid_input(self):
        """Test valid input creation."""
        input_data = KMZGenerationInput(
            flight_plan={"waypoints": [{"lat": 40.7, "lon": -74.0, "alt": 100}]},
            output_filename="test.kmz",
            include_template=True,
            author="Test User"
        )
        
        assert input_data.output_filename == "test.kmz"
        assert input_data.include_template is True
        assert input_data.author == "Test User"
    
    def test_default_values(self):
        """Test default values in input."""
        input_data = KMZGenerationInput(
            flight_plan={"waypoints": []}
        )
        
        assert input_data.output_filename == "mission.kmz"
        assert input_data.include_template is True
        assert input_data.include_resources is False
        assert input_data.author is None
    
    def test_required_fields(self):
        """Test required field validation."""
        with pytest.raises(Exception):  # Should raise validation error
            KMZGenerationInput()  # Missing required flight_plan


class TestKMZFileStructure:
    """Test cases for KMZ file structure compliance."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = KMZGenerationTool()
    
    @pytest.mark.asyncio
    async def test_kmz_file_structure(self):
        """Test that generated KMZ files have correct structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('dji_waypoint_mcp.tools.kmz_generation.settings') as mock_settings:
                mock_settings.output_dir = Path(temp_dir)
                
                arguments = {
                    "flight_plan": {
                        "waypoints": [
                            {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                            {"latitude": 40.7228, "longitude": -74.0160, "altitude": 120.0}
                        ]
                    },
                    "include_template": True,
                    "include_resources": True
                }
                
                result = await self.tool.execute(arguments)
                assert result["success"] is True
                
                # Verify KMZ file structure
                output_path = Path(temp_dir) / "mission.kmz"
                with zipfile.ZipFile(output_path, 'r') as kmz_file:
                    file_list = kmz_file.namelist()
                    
                    # Required files
                    assert 'wpmz/waylines.wpml' in file_list
                    assert 'wpmz/template.kml' in file_list
                    assert 'wpmz/res/' in file_list
                    
                    # Verify file contents are valid XML
                    waylines_content = kmz_file.read('wpmz/waylines.wpml').decode('utf-8')
                    template_content = kmz_file.read('wpmz/template.kml').decode('utf-8')
                    
                    # Parse to ensure valid XML
                    waylines_root = fromstring(waylines_content)
                    template_root = fromstring(template_content)
                    
                    assert waylines_root.tag == 'kml'
                    assert template_root.tag == 'kml'
    
    @pytest.mark.asyncio
    async def test_wpml_namespace_compliance(self):
        """Test WPML namespace compliance in generated files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('dji_waypoint_mcp.tools.kmz_generation.settings') as mock_settings:
                mock_settings.output_dir = Path(temp_dir)
                
                arguments = {
                    "flight_plan": {
                        "waypoints": [
                            {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0}
                        ]
                    }
                }
                
                result = await self.tool.execute(arguments)
                assert result["success"] is True
                
                output_path = Path(temp_dir) / "mission.kmz"
                with zipfile.ZipFile(output_path, 'r') as kmz_file:
                    waylines_content = kmz_file.read('wpmz/waylines.wpml').decode('utf-8')
                    
                    # Check for required namespaces
                    assert 'xmlns="http://www.opengis.net/kml/2.2"' in waylines_content
                    assert 'xmlns:wpml="http://www.dji.com/wpmz/1.0.2"' in waylines_content
                    
                    # Check for WPML-specific elements
                    assert '<wpml:missionConfig>' in waylines_content
                    assert '<wpml:executeHeightMode>' in waylines_content
                    assert '<wpml:waypointHeadingParam>' in waylines_content

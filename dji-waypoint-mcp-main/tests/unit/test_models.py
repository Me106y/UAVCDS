"""
Unit tests for data models.
"""

import pytest
from pydantic import ValidationError

from dji_waypoint_mcp.models import (
    Coordinates,
    Waypoint,
    FlightPath,
    AircraftModel,
    PayloadModel,
    AircraftSpecs,
    PayloadSpecs,
    MissionConfig,
    HeightMode,
    WaypointTurnMode,
)


class TestCoordinates:
    """Test cases for Coordinates model."""
    
    def test_valid_coordinates(self):
        """Test valid coordinate creation."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        assert coords.latitude == 40.7128
        assert coords.longitude == -74.0060
        assert coords.altitude == 100.0
    
    def test_invalid_latitude(self):
        """Test invalid latitude validation."""
        with pytest.raises(ValidationError):
            Coordinates(latitude=91.0, longitude=0.0)
        
        with pytest.raises(ValidationError):
            Coordinates(latitude=-91.0, longitude=0.0)
    
    def test_invalid_longitude(self):
        """Test invalid longitude validation."""
        with pytest.raises(ValidationError):
            Coordinates(latitude=0.0, longitude=181.0)
        
        with pytest.raises(ValidationError):
            Coordinates(latitude=0.0, longitude=-181.0)
    
    def test_kml_coordinates_format(self):
        """Test KML coordinate formatting."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        kml_format = coords.to_kml_coordinates()
        assert kml_format == "-74.006,40.7128,100.0"
        
        # Test without altitude
        coords_no_alt = Coordinates(latitude=40.7128, longitude=-74.0060)
        kml_format_no_alt = coords_no_alt.to_kml_coordinates()
        assert kml_format_no_alt == "-74.006,40.7128"


class TestWaypoint:
    """Test cases for Waypoint model."""
    
    def test_valid_waypoint(self):
        """Test valid waypoint creation."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        waypoint = Waypoint(index=0, coordinates=coords)
        
        assert waypoint.index == 0
        assert waypoint.coordinates == coords
        assert waypoint.use_global_height is True
        assert waypoint.use_global_speed is True
    
    def test_invalid_waypoint_index(self):
        """Test invalid waypoint index."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060)
        
        with pytest.raises(ValidationError):
            Waypoint(index=-1, coordinates=coords)


class TestFlightPath:
    """Test cases for FlightPath model."""
    
    def test_valid_flight_path(self):
        """Test valid flight path creation."""
        coords1 = Coordinates(latitude=40.7128, longitude=-74.0060)
        coords2 = Coordinates(latitude=40.7589, longitude=-73.9851)
        
        waypoint1 = Waypoint(index=0, coordinates=coords1)
        waypoint2 = Waypoint(index=1, coordinates=coords2)
        
        flight_path = FlightPath(waypoints=[waypoint1, waypoint2])
        
        assert len(flight_path.waypoints) == 2
        assert flight_path.global_speed == 5.0
        assert flight_path.height_mode == HeightMode.EGM96
    
    def test_insufficient_waypoints(self):
        """Test flight path with insufficient waypoints."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060)
        waypoint = Waypoint(index=0, coordinates=coords)
        
        with pytest.raises(ValidationError):
            FlightPath(waypoints=[waypoint])
    
    def test_waypoint_index_validation(self):
        """Test waypoint index sequence validation."""
        coords1 = Coordinates(latitude=40.7128, longitude=-74.0060)
        coords2 = Coordinates(latitude=40.7589, longitude=-73.9851)
        
        waypoint1 = Waypoint(index=0, coordinates=coords1)
        waypoint2 = Waypoint(index=2, coordinates=coords2)  # Wrong index
        
        with pytest.raises(ValidationError):
            FlightPath(waypoints=[waypoint1, waypoint2])


class TestAircraftSpecs:
    """Test cases for AircraftSpecs model."""
    
    def test_valid_aircraft_specs(self):
        """Test valid aircraft specs creation."""
        specs = AircraftSpecs(
            model=AircraftModel.M30,
            enum_value=67,
            max_flight_speed=15.0,
            max_flight_height=500.0,
            max_flight_distance=50000.0,
            battery_life=45.0,
            supported_payloads=[PayloadModel.M30_DUAL_CAMERA]
        )
        
        assert specs.model == AircraftModel.M30
        assert specs.enum_value == 67
        assert specs.max_flight_speed == 15.0
        assert PayloadModel.M30_DUAL_CAMERA in specs.supported_payloads


class TestPayloadSpecs:
    """Test cases for PayloadSpecs model."""
    
    def test_valid_payload_specs(self):
        """Test valid payload specs creation."""
        specs = PayloadSpecs(
            model=PayloadModel.M30_DUAL_CAMERA,
            enum_value=52,
            has_zoom=True,
            has_thermal=False,
            gimbal_pitch_range=(-90, 30),
            supported_image_formats=["wide", "zoom"]
        )
        
        assert specs.model == PayloadModel.M30_DUAL_CAMERA
        assert specs.enum_value == 52
        assert specs.has_zoom is True
        assert specs.has_thermal is False
        assert "wide" in specs.supported_image_formats


class TestMissionConfig:
    """Test cases for MissionConfig model."""
    
    def test_valid_mission_config(self):
        """Test valid mission config creation."""
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
        
        config = MissionConfig(aircraft=aircraft, payload=payload)
        
        assert config.aircraft.model == AircraftModel.M30
        assert config.payload.model == PayloadModel.M30_DUAL_CAMERA
        assert config.takeoff_security_height == 20.0
        assert config.global_transitional_speed == 8.0
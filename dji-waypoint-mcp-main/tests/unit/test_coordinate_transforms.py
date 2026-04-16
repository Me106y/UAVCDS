"""
Unit tests for coordinate transformation utilities.
"""

import pytest
import math
from unittest.mock import patch, MagicMock

from dji_waypoint_mcp.utils.coordinate_transforms import CoordinateTransformer, coordinate_transformer
from dji_waypoint_mcp.models import Coordinates, CoordinateSystem, CoordinateTransform


class TestCoordinateTransformer:
    """Test cases for coordinate transformation utilities."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = CoordinateTransformer()
    
    def test_same_system_transformation(self):
        """Test transformation between same coordinate systems."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        
        result = self.transformer.transform_coordinates(
            coords, CoordinateSystem.WGS84, CoordinateSystem.WGS84
        )
        
        assert result.latitude == coords.latitude
        assert result.longitude == coords.longitude
        assert result.altitude == coords.altitude
    
    def test_wgs84_to_egm96_transformation(self):
        """Test WGS84 to EGM96 transformation."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        
        result = self.transformer.transform_coordinates(
            coords, CoordinateSystem.WGS84, CoordinateSystem.EGM96
        )
        
        # Result should have different altitude due to geoid height
        assert result.latitude == coords.latitude
        assert result.longitude == coords.longitude
        assert result.altitude != coords.altitude
    
    def test_egm96_to_wgs84_transformation(self):
        """Test EGM96 to WGS84 transformation."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        
        result = self.transformer.transform_coordinates(
            coords, CoordinateSystem.EGM96, CoordinateSystem.WGS84
        )
        
        # Result should have different altitude due to geoid height
        assert result.latitude == coords.latitude
        assert result.longitude == coords.longitude
        assert result.altitude != coords.altitude
    
    def test_roundtrip_transformation(self):
        """Test roundtrip transformation WGS84 -> EGM96 -> WGS84."""
        original = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        
        # Transform to EGM96
        egm96_coords = self.transformer.transform_coordinates(
            original, CoordinateSystem.WGS84, CoordinateSystem.EGM96
        )
        
        # Transform back to WGS84
        result = self.transformer.transform_coordinates(
            egm96_coords, CoordinateSystem.EGM96, CoordinateSystem.WGS84
        )
        
        # Should be close to original (within reasonable tolerance)
        assert abs(result.latitude - original.latitude) < 0.0001
        assert abs(result.longitude - original.longitude) < 0.0001
        assert abs(result.altitude - original.altitude) < 1.0  # 1m tolerance
    
    def test_relative_coordinate_transformation(self):
        """Test transformation to relative coordinates."""
        reference = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        target = Coordinates(latitude=40.7228, longitude=-74.0060, altitude=120.0)  # ~1km north, 20m up
        
        result = self.transformer.transform_coordinates(
            target, CoordinateSystem.WGS84, CoordinateSystem.RELATIVE_TO_START, reference
        )
        
        # Should be approximately 1000m north (stored as latitude), 0m east (longitude), 20m up
        assert abs(result.latitude - 1000) < 100  # Within 100m tolerance
        assert abs(result.longitude) < 10  # Should be close to 0
        assert abs(result.altitude - 20) < 1  # Should be 20m up
    
    def test_from_relative_coordinates(self):
        """Test transformation from relative coordinates."""
        reference = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        relative = Coordinates(latitude=1000.0, longitude=0.0, altitude=20.0)  # 1km north, 20m up
        
        result = self.transformer.transform_coordinates(
            relative, CoordinateSystem.RELATIVE_TO_START, CoordinateSystem.WGS84, reference
        )
        
        # Should be approximately 1km north of reference point
        expected_lat = 40.7128 + (1000 / 111000)  # Approximate degrees per meter
        assert abs(result.latitude - expected_lat) < 0.001
        assert abs(result.longitude - reference.longitude) < 0.001
        assert abs(result.altitude - 120.0) < 1.0
    
    def test_relative_transformation_without_reference(self):
        """Test relative transformation without reference point raises error."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        
        with pytest.raises(ValueError, match="Reference point required"):
            self.transformer.transform_coordinates(
                coords, CoordinateSystem.WGS84, CoordinateSystem.RELATIVE_TO_START
            )
    
    def test_distance_and_bearing_calculation(self):
        """Test distance and bearing calculation."""
        point1 = Coordinates(latitude=0.0, longitude=0.0)
        point2 = Coordinates(latitude=1.0, longitude=0.0)  # 1 degree north
        
        distance, bearing = self.transformer._calculate_distance_and_bearing(point1, point2)
        
        # Should be approximately 111km north (bearing = 0)
        assert 110000 < distance < 112000
        assert abs(bearing - 0) < 1  # Should be due north
    
    def test_destination_point_calculation(self):
        """Test destination point calculation."""
        start = Coordinates(latitude=0.0, longitude=0.0)
        distance = 111000  # Approximately 1 degree
        bearing = 0  # Due north
        
        result = self.transformer._calculate_destination_point(start, distance, bearing)
        
        # Should be approximately 1 degree north
        assert abs(result.latitude - 1.0) < 0.01
        assert abs(result.longitude - 0.0) < 0.01
    
    def test_batch_transformation(self):
        """Test batch coordinate transformation."""
        coords_list = [
            Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0),
            Coordinates(latitude=40.7228, longitude=-74.0160, altitude=120.0),
            Coordinates(latitude=40.7328, longitude=-74.0260, altitude=140.0)
        ]
        
        results = self.transformer.batch_transform(
            coords_list, CoordinateSystem.WGS84, CoordinateSystem.EGM96
        )
        
        assert len(results) == len(coords_list)
        for i, result in enumerate(results):
            assert result.latitude == coords_list[i].latitude
            assert result.longitude == coords_list[i].longitude
            assert result.altitude != coords_list[i].altitude  # Should be transformed
    
    def test_coordinate_precision_validation(self):
        """Test coordinate precision validation."""
        # High precision coordinates
        high_precision = Coordinates(latitude=40.712812345, longitude=-74.006012345, altitude=100.0)
        result = self.transformer.validate_coordinate_precision(high_precision)
        
        assert result["is_valid"] is True
        assert result["precision"]["latitude_decimals"] >= 6
        assert result["precision"]["longitude_decimals"] >= 6
        
        # Low precision coordinates
        low_precision = Coordinates(latitude=40.71, longitude=-74.01, altitude=100.0)
        result = self.transformer.validate_coordinate_precision(low_precision)
        
        assert result["is_valid"] is False
        assert len(result["warnings"]) > 0
        assert "precision" in result["warnings"][0]
    
    def test_extreme_coordinates_validation(self):
        """Test validation of extreme coordinates."""
        # Near pole coordinates
        polar_coords = Coordinates(latitude=89.0, longitude=0.0, altitude=100.0)
        result = self.transformer.validate_coordinate_precision(polar_coords)
        
        assert "poles" in str(result["warnings"])
        
        # Extreme altitude
        extreme_alt = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=15000.0)
        result = self.transformer.validate_coordinate_precision(extreme_alt)
        
        assert "altitude" in str(result["warnings"]).lower()
    
    def test_approximate_geoid_height_calculation(self):
        """Test approximate geoid height calculation."""
        # Test at equator
        geoid_height_equator = self.transformer._calculate_approximate_geoid_height(0.0, 0.0)
        assert isinstance(geoid_height_equator, float)
        
        # Test at different locations
        geoid_height_ny = self.transformer._calculate_approximate_geoid_height(40.7128, -74.0060)
        assert isinstance(geoid_height_ny, float)
        
        # Results should be different for different locations
        assert geoid_height_equator != geoid_height_ny
    
    @patch('dji_waypoint_mcp.utils.coordinate_transforms.Transformer')
    def test_pyproj_fallback(self, mock_transformer):
        """Test fallback to approximate transformations when pyproj fails."""
        # Mock pyproj to raise an exception
        mock_transformer.from_crs.side_effect = Exception("PyProj error")
        
        # Create new transformer instance
        transformer = CoordinateTransformer()
        
        # Should still work with approximate transformations
        coords = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        result = transformer.transform_coordinates(
            coords, CoordinateSystem.WGS84, CoordinateSystem.EGM96
        )
        
        assert result is not None
        assert result.altitude != coords.altitude


class TestCoordinateTransformModel:
    """Test cases for CoordinateTransform model."""
    
    def test_coordinate_transform_creation(self):
        """Test CoordinateTransform model creation."""
        transform = CoordinateTransform(
            source_system=CoordinateSystem.WGS84,
            target_system=CoordinateSystem.EGM96
        )
        
        assert transform.source_system == CoordinateSystem.WGS84
        assert transform.target_system == CoordinateSystem.EGM96
        assert transform.reference_point is None
    
    def test_coordinate_transform_with_reference(self):
        """Test CoordinateTransform with reference point."""
        reference = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        transform = CoordinateTransform(
            source_system=CoordinateSystem.WGS84,
            target_system=CoordinateSystem.RELATIVE_TO_START,
            reference_point=reference
        )
        
        assert transform.reference_point == reference
    
    def test_transform_method(self):
        """Test the transform method of CoordinateTransform."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        transform = CoordinateTransform(
            source_system=CoordinateSystem.WGS84,
            target_system=CoordinateSystem.EGM96
        )
        
        result = transform.transform(coords)
        
        assert result is not None
        assert result.latitude == coords.latitude
        assert result.longitude == coords.longitude
        # Altitude should be different due to transformation
        assert result.altitude != coords.altitude


class TestGlobalTransformerInstance:
    """Test the global coordinate transformer instance."""
    
    def test_global_instance_exists(self):
        """Test that global transformer instance exists."""
        assert coordinate_transformer is not None
        assert isinstance(coordinate_transformer, CoordinateTransformer)
    
    def test_global_instance_functionality(self):
        """Test that global instance works correctly."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        
        result = coordinate_transformer.transform_coordinates(
            coords, CoordinateSystem.WGS84, CoordinateSystem.EGM96
        )
        
        assert result is not None
        assert result.latitude == coords.latitude
        assert result.longitude == coords.longitude
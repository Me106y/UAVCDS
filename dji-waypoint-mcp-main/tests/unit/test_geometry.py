"""
Unit tests for geometry calculation utilities.
"""

import pytest
import math
from unittest.mock import patch

from dji_waypoint_mcp.utils.geometry import GeometryCalculator, geometry_calculator
from dji_waypoint_mcp.models import Coordinates


class TestGeometryCalculator:
    """Test cases for geometry calculation utilities."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calc = GeometryCalculator()
        
        # Test coordinates (NYC area)
        self.coord1 = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        self.coord2 = Coordinates(latitude=40.7228, longitude=-74.0060, altitude=120.0)  # ~1.1km north
        self.coord3 = Coordinates(latitude=40.7128, longitude=-73.9960, altitude=100.0)  # ~0.8km east
        
        # Test polygon (square)
        self.square_polygon = [
            Coordinates(latitude=40.7128, longitude=-74.0060),
            Coordinates(latitude=40.7228, longitude=-74.0060),
            Coordinates(latitude=40.7228, longitude=-73.9960),
            Coordinates(latitude=40.7128, longitude=-73.9960)
        ]
    
    def test_haversine_distance(self):
        """Test Haversine distance calculation."""
        # Test horizontal distance
        distance = self.calc.haversine_distance(self.coord1, self.coord2)
        assert 1000 < distance < 1200  # Should be ~1.1km
        
        # Test 3D distance with altitude difference
        distance_3d = self.calc.haversine_distance(self.coord1, self.coord2)
        horizontal_only = self.calc.haversine_distance(
            Coordinates(latitude=40.7128, longitude=-74.0060),
            Coordinates(latitude=40.7228, longitude=-74.0060)
        )
        
        # 3D distance should be slightly larger due to altitude difference
        assert distance_3d >= horizontal_only
    
    def test_calculate_bearing(self):
        """Test bearing calculation."""
        # North bearing
        bearing_north = self.calc.calculate_bearing(self.coord1, self.coord2)
        assert abs(bearing_north - 0) < 5  # Should be close to 0° (north)
        
        # East bearing
        bearing_east = self.calc.calculate_bearing(self.coord1, self.coord3)
        assert abs(bearing_east - 90) < 5  # Should be close to 90° (east)
        
        # Test bearing range
        assert 0 <= bearing_north <= 360
        assert 0 <= bearing_east <= 360
    
    def test_destination_point(self):
        """Test destination point calculation."""
        # Calculate point 1000m north
        destination = self.calc.destination_point(self.coord1, 1000.0, 0.0)
        
        # Should be approximately at coord2's latitude
        assert abs(destination.latitude - self.coord2.latitude) < 0.001
        assert abs(destination.longitude - self.coord1.longitude) < 0.001
        
        # Test east direction
        destination_east = self.calc.destination_point(self.coord1, 800.0, 90.0)
        assert destination_east.longitude > self.coord1.longitude
        assert abs(destination_east.latitude - self.coord1.latitude) < 0.001
    
    def test_polygon_area(self):
        """Test polygon area calculation."""
        area = self.calc.polygon_area(self.square_polygon)
        
        assert area > 0
        # Should be roughly 1.1km × 0.8km = 0.88 km² = 880,000 m²
        assert 800000 < area < 1000000
    
    def test_polygon_centroid(self):
        """Test polygon centroid calculation."""
        centroid = self.calc.polygon_centroid(self.square_polygon)
        
        # Centroid should be in the middle of the square
        expected_lat = (40.7128 + 40.7228) / 2
        expected_lon = (-74.0060 + -73.9960) / 2
        
        assert abs(centroid.latitude - expected_lat) < 0.001
        assert abs(centroid.longitude - expected_lon) < 0.001
    
    def test_expand_polygon(self):
        """Test polygon expansion."""
        expanded = self.calc.expand_polygon(self.square_polygon, 100.0)  # 100m expansion
        
        assert len(expanded) >= len(self.square_polygon)
        
        # Expanded polygon should have larger area
        original_area = self.calc.polygon_area(self.square_polygon)
        expanded_area = self.calc.polygon_area(expanded)
        assert expanded_area > original_area
    
    def test_point_in_polygon(self):
        """Test point in polygon check."""
        # Point inside polygon
        inside_point = Coordinates(latitude=40.7178, longitude=-74.0010)
        assert self.calc.point_in_polygon(inside_point, self.square_polygon) is True
        
        # Point outside polygon
        outside_point = Coordinates(latitude=40.7300, longitude=-74.0060)
        assert self.calc.point_in_polygon(outside_point, self.square_polygon) is False
    
    def test_polygon_intersection(self):
        """Test polygon intersection."""
        # Create overlapping polygon
        overlapping_polygon = [
            Coordinates(latitude=40.7178, longitude=-74.0010),
            Coordinates(latitude=40.7278, longitude=-74.0010),
            Coordinates(latitude=40.7278, longitude=-73.9910),
            Coordinates(latitude=40.7178, longitude=-73.9910)
        ]
        
        intersections = self.calc.polygon_intersection(self.square_polygon, overlapping_polygon)
        
        assert len(intersections) > 0
        # Should have some intersection area
        if intersections:
            intersection_area = self.calc.polygon_area(intersections[0])
            assert intersection_area > 0
    
    def test_line_polygon_intersection(self):
        """Test line-polygon intersection."""
        # Line crossing the polygon
        line_start = Coordinates(latitude=40.7100, longitude=-74.0030)
        line_end = Coordinates(latitude=40.7250, longitude=-74.0030)
        
        intersections = self.calc.line_polygon_intersection(
            line_start, line_end, self.square_polygon
        )
        
        assert len(intersections) > 0
        # Should have intersection segments
        for start, end in intersections:
            assert isinstance(start, Coordinates)
            assert isinstance(end, Coordinates)
    
    def test_simplify_polygon(self):
        """Test polygon simplification."""
        # Create polygon with many points
        detailed_polygon = []
        for i in range(20):
            angle = 2 * math.pi * i / 20
            lat = 40.7178 + 0.01 * math.cos(angle)
            lon = -74.0010 + 0.01 * math.sin(angle)
            detailed_polygon.append(Coordinates(latitude=lat, longitude=lon))
        
        simplified = self.calc.simplify_polygon(detailed_polygon, tolerance=0.001)
        
        # Simplified polygon should have fewer points
        assert len(simplified) <= len(detailed_polygon)
        assert len(simplified) >= 3  # Still a valid polygon
    
    def test_generate_grid_points(self):
        """Test grid point generation."""
        bounds = (-74.0060, 40.7128, -73.9960, 40.7228)  # min_lon, min_lat, max_lon, max_lat
        spacing = 200.0  # 200 meters
        
        grid_points = self.calc.generate_grid_points(bounds, spacing)
        
        assert len(grid_points) > 0
        
        # All points should be within bounds
        for point in grid_points:
            assert bounds[1] <= point.latitude <= bounds[3]
            assert bounds[0] <= point.longitude <= bounds[2]
    
    def test_generate_concentric_polygons(self):
        """Test concentric polygon generation."""
        center = Coordinates(latitude=40.7178, longitude=-74.0010)
        radius = 500.0  # 500 meters
        num_sides = 6
        num_rings = 3
        
        polygons = self.calc.generate_concentric_polygons(center, radius, num_sides, num_rings)
        
        assert len(polygons) == num_rings
        
        for polygon in polygons:
            assert len(polygon) == num_sides
            
            # All points should be roughly equidistant from center
            distances = [self.calc.haversine_distance(center, point) for point in polygon]
            avg_distance = sum(distances) / len(distances)
            
            # Distances should be similar (within 10% tolerance)
            for distance in distances:
                assert abs(distance - avg_distance) / avg_distance < 0.1
    
    def test_calculate_polygon_perimeter(self):
        """Test polygon perimeter calculation."""
        perimeter = self.calc.calculate_polygon_perimeter(self.square_polygon)
        
        assert perimeter > 0
        # Should be roughly 2 * (1.1km + 0.8km) = 3.8km
        assert 3500 < perimeter < 4200
    
    def test_find_polygon_bounds(self):
        """Test polygon bounds calculation."""
        bounds = self.calc.find_polygon_bounds(self.square_polygon)
        min_lon, min_lat, max_lon, max_lat = bounds
        
        assert min_lon == -74.0060
        assert max_lon == -73.9960
        assert min_lat == 40.7128
        assert max_lat == 40.7228
    
    def test_rotate_polygon(self):
        """Test polygon rotation."""
        rotated = self.calc.rotate_polygon(self.square_polygon, 45.0)
        
        assert len(rotated) == len(self.square_polygon)
        
        # Rotated polygon should have different coordinates
        assert rotated[0].latitude != self.square_polygon[0].latitude
        assert rotated[0].longitude != self.square_polygon[0].longitude
        
        # But same area (approximately)
        original_area = self.calc.polygon_area(self.square_polygon)
        rotated_area = self.calc.polygon_area(rotated)
        assert abs(rotated_area - original_area) / original_area < 0.1
    
    def test_scale_polygon(self):
        """Test polygon scaling."""
        scaled = self.calc.scale_polygon(self.square_polygon, 2.0)
        
        assert len(scaled) == len(self.square_polygon)
        
        # Scaled polygon should have 4x the area (2² scaling factor)
        original_area = self.calc.polygon_area(self.square_polygon)
        scaled_area = self.calc.polygon_area(scaled)
        assert abs(scaled_area / original_area - 4.0) < 0.5
    
    def test_translate_polygon(self):
        """Test polygon translation."""
        offset_x, offset_y = 0.01, 0.01  # degrees
        translated = self.calc.translate_polygon(self.square_polygon, offset_x, offset_y)
        
        assert len(translated) == len(self.square_polygon)
        
        # All points should be shifted by the offset
        for i, point in enumerate(translated):
            original = self.square_polygon[i]
            assert abs(point.longitude - original.longitude - offset_x) < 0.0001
            assert abs(point.latitude - original.latitude - offset_y) < 0.0001
    
    def test_calculate_optimal_flight_direction(self):
        """Test optimal flight direction calculation."""
        direction = self.calc.calculate_optimal_flight_direction(self.square_polygon)
        
        assert 0 <= direction <= 360
        
        # For a square aligned with lat/lon, optimal direction should be ~0° or ~90°
        assert abs(direction) < 10 or abs(direction - 90) < 10 or abs(direction - 180) < 10 or abs(direction - 270) < 10
    
    def test_calculate_minimum_bounding_rectangle(self):
        """Test minimum bounding rectangle calculation."""
        rect_coords, orientation = self.calc.calculate_minimum_bounding_rectangle(self.square_polygon)
        
        assert len(rect_coords) >= 3
        assert 0 <= orientation <= 360
        
        # Rectangle area should be close to original polygon area
        original_area = self.calc.polygon_area(self.square_polygon)
        rect_area = self.calc.polygon_area(rect_coords)
        assert rect_area >= original_area  # Rectangle should contain the polygon
    
    def test_validate_polygon(self):
        """Test polygon validation."""
        # Valid polygon
        validation = self.calc.validate_polygon(self.square_polygon)
        assert validation["is_valid"] is True
        assert len(validation["errors"]) == 0
        assert validation["area_m2"] > 0
        assert validation["perimeter_m"] > 0
        
        # Invalid polygon (too few points)
        invalid_polygon = [
            Coordinates(latitude=40.7128, longitude=-74.0060),
            Coordinates(latitude=40.7228, longitude=-74.0060)
        ]
        validation = self.calc.validate_polygon(invalid_polygon)
        assert validation["is_valid"] is False
        assert len(validation["errors"]) > 0
        
        # Very small polygon (should have warnings)
        small_polygon = [
            Coordinates(latitude=40.7128, longitude=-74.0060),
            Coordinates(latitude=40.7129, longitude=-74.0060),
            Coordinates(latitude=40.7129, longitude=-74.0059)
        ]
        validation = self.calc.validate_polygon(small_polygon)
        # May be valid but should have warnings about small area
        if validation["is_valid"]:
            assert len(validation["warnings"]) > 0
    
    def test_empty_coordinates_handling(self):
        """Test handling of empty coordinate lists."""
        with pytest.raises(ValueError):
            self.calc.polygon_centroid([])
        
        assert self.calc.polygon_area([]) == 0.0
        assert self.calc.calculate_polygon_perimeter([]) == 0.0
        
        bounds = self.calc.find_polygon_bounds([])
        assert bounds == (0.0, 0.0, 0.0, 0.0)
    
    def test_single_point_handling(self):
        """Test handling of single point."""
        single_point = [Coordinates(latitude=40.7128, longitude=-74.0060)]
        
        assert self.calc.polygon_area(single_point) == 0.0
        assert self.calc.calculate_polygon_perimeter(single_point) == 0.0
        
        validation = self.calc.validate_polygon(single_point)
        assert validation["is_valid"] is False
    
    def test_coordinate_precision(self):
        """Test calculations with high precision coordinates."""
        high_precision_coords = [
            Coordinates(latitude=40.712812345, longitude=-74.006012345),
            Coordinates(latitude=40.722812345, longitude=-74.006012345),
            Coordinates(latitude=40.722812345, longitude=-73.996012345),
            Coordinates(latitude=40.712812345, longitude=-73.996012345)
        ]
        
        area = self.calc.polygon_area(high_precision_coords)
        centroid = self.calc.polygon_centroid(high_precision_coords)
        perimeter = self.calc.calculate_polygon_perimeter(high_precision_coords)
        
        assert area > 0
        assert centroid.latitude > 0
        assert centroid.longitude < 0
        assert perimeter > 0
    
    def test_large_polygon_handling(self):
        """Test handling of large polygons."""
        # Create a large polygon (roughly 100km x 100km)
        large_polygon = [
            Coordinates(latitude=40.0, longitude=-74.0),
            Coordinates(latitude=41.0, longitude=-74.0),
            Coordinates(latitude=41.0, longitude=-73.0),
            Coordinates(latitude=40.0, longitude=-73.0)
        ]
        
        area = self.calc.polygon_area(large_polygon)
        perimeter = self.calc.calculate_polygon_perimeter(large_polygon)
        
        assert area > 1e9  # Should be > 1 billion square meters
        assert perimeter > 400000  # Should be > 400km
        
        validation = self.calc.validate_polygon(large_polygon)
        assert validation["is_valid"] is True


class TestGlobalGeometryCalculator:
    """Test the global geometry calculator instance."""
    
    def test_global_instance_exists(self):
        """Test that global geometry calculator instance exists."""
        assert geometry_calculator is not None
        assert isinstance(geometry_calculator, GeometryCalculator)
    
    def test_global_instance_functionality(self):
        """Test that global instance works correctly."""
        coord1 = Coordinates(latitude=40.7128, longitude=-74.0060)
        coord2 = Coordinates(latitude=40.7228, longitude=-74.0060)
        
        distance = geometry_calculator.haversine_distance(coord1, coord2)
        bearing = geometry_calculator.calculate_bearing(coord1, coord2)
        
        assert distance > 0
        assert 0 <= bearing <= 360


class TestGeometryEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calc = GeometryCalculator()
    
    def test_identical_coordinates(self):
        """Test calculations with identical coordinates."""
        coord = Coordinates(latitude=40.7128, longitude=-74.0060)
        
        distance = self.calc.haversine_distance(coord, coord)
        assert distance == 0.0
        
        # Bearing of identical points is undefined, but should not crash
        bearing = self.calc.calculate_bearing(coord, coord)
        assert isinstance(bearing, float)
    
    def test_antipodal_points(self):
        """Test calculations with antipodal points."""
        coord1 = Coordinates(latitude=40.7128, longitude=-74.0060)
        coord2 = Coordinates(latitude=-40.7128, longitude=105.9940)  # Roughly antipodal
        
        distance = self.calc.haversine_distance(coord1, coord2)
        # Should be roughly half the Earth's circumference
        expected_distance = math.pi * self.calc.earth_radius
        assert abs(distance - expected_distance) / expected_distance < 0.1
    
    def test_extreme_coordinates(self):
        """Test calculations with extreme coordinates."""
        # Near poles
        north_pole = Coordinates(latitude=89.9, longitude=0.0)
        south_pole = Coordinates(latitude=-89.9, longitude=0.0)
        
        distance = self.calc.haversine_distance(north_pole, south_pole)
        assert distance > 0
        
        # Near date line
        coord1 = Coordinates(latitude=0.0, longitude=179.9)
        coord2 = Coordinates(latitude=0.0, longitude=-179.9)
        
        distance = self.calc.haversine_distance(coord1, coord2)
        assert distance > 0
        assert distance < 100000  # Should be short distance across date line
    
    def test_self_intersecting_polygon(self):
        """Test handling of self-intersecting polygon."""
        # Create a figure-8 polygon
        self_intersecting = [
            Coordinates(latitude=40.7128, longitude=-74.0060),
            Coordinates(latitude=40.7228, longitude=-73.9960),
            Coordinates(latitude=40.7228, longitude=-74.0060),
            Coordinates(latitude=40.7128, longitude=-73.9960)
        ]
        
        validation = self.calc.validate_polygon(self_intersecting)
        # Should be detected as invalid
        assert validation["is_valid"] is False
        assert any("intersection" in error.lower() for error in validation["errors"])
    
    def test_very_small_polygon(self):
        """Test handling of very small polygon."""
        tiny_polygon = [
            Coordinates(latitude=40.712800, longitude=-74.006000),
            Coordinates(latitude=40.712801, longitude=-74.006000),
            Coordinates(latitude=40.712801, longitude=-74.005999)
        ]
        
        area = self.calc.polygon_area(tiny_polygon)
        validation = self.calc.validate_polygon(tiny_polygon)
        
        assert area >= 0
        if validation["is_valid"]:
            assert len(validation["warnings"]) > 0  # Should warn about small area
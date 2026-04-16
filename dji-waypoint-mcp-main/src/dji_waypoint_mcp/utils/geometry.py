"""
Geometry calculation utilities for flight planning.
"""

import math
from typing import List, Tuple, Optional, Union
import numpy as np
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely.ops import unary_union, transform
from shapely.affinity import rotate, scale, translate
import logging

from ..models import Coordinates

logger = logging.getLogger(__name__)


class GeometryCalculator:
    """Comprehensive geometry calculations for flight planning."""
    
    def __init__(self):
        """Initialize the geometry calculator."""
        self.earth_radius = 6371000  # Earth radius in meters
    
    # Distance and bearing calculations
    
    def haversine_distance(self, coord1: Coordinates, coord2: Coordinates) -> float:
        """Calculate distance between two coordinates using Haversine formula."""
        lat1, lon1 = math.radians(coord1.latitude), math.radians(coord1.longitude)
        lat2, lon2 = math.radians(coord2.latitude), math.radians(coord2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Add vertical distance if altitudes are available
        horizontal_distance = self.earth_radius * c
        
        if coord1.altitude is not None and coord2.altitude is not None:
            vertical_distance = abs(coord2.altitude - coord1.altitude)
            return math.sqrt(horizontal_distance**2 + vertical_distance**2)
        
        return horizontal_distance
    
    def calculate_bearing(self, coord1: Coordinates, coord2: Coordinates) -> float:
        """Calculate bearing from coord1 to coord2 in degrees (0-360)."""
        lat1, lon1 = math.radians(coord1.latitude), math.radians(coord1.longitude)
        lat2, lon2 = math.radians(coord2.latitude), math.radians(coord2.longitude)
        
        dlon = lon2 - lon1
        
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360) % 360
    
    def destination_point(
        self, 
        start: Coordinates, 
        distance: float, 
        bearing: float
    ) -> Coordinates:
        """Calculate destination point given start point, distance, and bearing."""
        lat1 = math.radians(start.latitude)
        lon1 = math.radians(start.longitude)
        bearing_rad = math.radians(bearing)
        
        lat2 = math.asin(
            math.sin(lat1) * math.cos(distance / self.earth_radius) +
            math.cos(lat1) * math.sin(distance / self.earth_radius) * math.cos(bearing_rad)
        )
        
        lon2 = lon1 + math.atan2(
            math.sin(bearing_rad) * math.sin(distance / self.earth_radius) * math.cos(lat1),
            math.cos(distance / self.earth_radius) - math.sin(lat1) * math.sin(lat2)
        )
        
        return Coordinates(
            latitude=math.degrees(lat2),
            longitude=math.degrees(lon2),
            altitude=start.altitude
        )
    
    # Polygon operations
    
    def polygon_area(self, coordinates: List[Coordinates]) -> float:
        """Calculate polygon area in square meters."""
        if len(coordinates) < 3:
            return 0.0
        
        # Convert to Shapely polygon
        polygon_coords = [(coord.longitude, coord.latitude) for coord in coordinates]
        polygon = Polygon(polygon_coords)
        
        # Calculate area in square degrees
        area_sq_degrees = polygon.area
        
        # Convert to square meters (approximate)
        # This is a rough approximation - for precise calculations, use projected coordinates
        center_lat = sum(coord.latitude for coord in coordinates) / len(coordinates)
        lat_factor = math.cos(math.radians(center_lat))
        
        # Degrees to meters conversion
        deg_to_m_lat = self.earth_radius * math.pi / 180
        deg_to_m_lon = deg_to_m_lat * lat_factor
        
        area_sq_meters = area_sq_degrees * deg_to_m_lat * deg_to_m_lon
        return abs(area_sq_meters)
    
    def polygon_centroid(self, coordinates: List[Coordinates]) -> Coordinates:
        """Calculate polygon centroid."""
        if not coordinates:
            raise ValueError("Empty coordinates list")
        
        polygon_coords = [(coord.longitude, coord.latitude) for coord in coordinates]
        polygon = Polygon(polygon_coords)
        centroid = polygon.centroid
        
        # Calculate average altitude if available
        altitudes = [coord.altitude for coord in coordinates if coord.altitude is not None]
        avg_altitude = sum(altitudes) / len(altitudes) if altitudes else None
        
        return Coordinates(
            latitude=centroid.y,
            longitude=centroid.x,
            altitude=avg_altitude
        )
    
    def expand_polygon(
        self, 
        coordinates: List[Coordinates], 
        distance: float
    ) -> List[Coordinates]:
        """Expand polygon outward by specified distance in meters."""
        polygon_coords = [(coord.longitude, coord.latitude) for coord in coordinates]
        polygon = Polygon(polygon_coords)
        
        # Convert distance from meters to degrees (approximate)
        center_lat = sum(coord.latitude for coord in coordinates) / len(coordinates)
        lat_factor = math.cos(math.radians(center_lat))
        distance_degrees = distance / (self.earth_radius * math.pi / 180 * lat_factor)
        
        # Buffer the polygon
        expanded_polygon = polygon.buffer(distance_degrees)
        
        # Convert back to coordinates
        if isinstance(expanded_polygon, Polygon):
            exterior_coords = list(expanded_polygon.exterior.coords)
            return [
                Coordinates(latitude=lat, longitude=lon, altitude=coordinates[0].altitude)
                for lon, lat in exterior_coords[:-1]  # Exclude duplicate closing point
            ]
        else:
            # Handle MultiPolygon case - return largest polygon
            if isinstance(expanded_polygon, MultiPolygon):
                largest_polygon = max(expanded_polygon.geoms, key=lambda p: p.area)
                exterior_coords = list(largest_polygon.exterior.coords)
                return [
                    Coordinates(latitude=lat, longitude=lon, altitude=coordinates[0].altitude)
                    for lon, lat in exterior_coords[:-1]
                ]
        
        return coordinates  # Fallback
    
    def point_in_polygon(self, point: Coordinates, polygon: List[Coordinates]) -> bool:
        """Check if point is inside polygon."""
        polygon_coords = [(coord.longitude, coord.latitude) for coord in polygon]
        shapely_polygon = Polygon(polygon_coords)
        shapely_point = Point(point.longitude, point.latitude)
        
        return shapely_polygon.contains(shapely_point)
    
    def polygon_intersection(
        self, 
        polygon1: List[Coordinates], 
        polygon2: List[Coordinates]
    ) -> List[List[Coordinates]]:
        """Calculate intersection of two polygons."""
        poly1_coords = [(coord.longitude, coord.latitude) for coord in polygon1]
        poly2_coords = [(coord.longitude, coord.latitude) for coord in polygon2]
        
        shapely_poly1 = Polygon(poly1_coords)
        shapely_poly2 = Polygon(poly2_coords)
        
        intersection = shapely_poly1.intersection(shapely_poly2)
        
        result = []
        if isinstance(intersection, Polygon):
            exterior_coords = list(intersection.exterior.coords)
            coords = [
                Coordinates(latitude=lat, longitude=lon)
                for lon, lat in exterior_coords[:-1]
            ]
            result.append(coords)
        elif isinstance(intersection, MultiPolygon):
            for poly in intersection.geoms:
                exterior_coords = list(poly.exterior.coords)
                coords = [
                    Coordinates(latitude=lat, longitude=lon)
                    for lon, lat in exterior_coords[:-1]
                ]
                result.append(coords)
        
        return result
    
    # Line operations
    
    def line_polygon_intersection(
        self, 
        line_start: Coordinates, 
        line_end: Coordinates, 
        polygon: List[Coordinates]
    ) -> List[Tuple[Coordinates, Coordinates]]:
        """Find intersection segments of line with polygon."""
        line = LineString([
            (line_start.longitude, line_start.latitude),
            (line_end.longitude, line_end.latitude)
        ])
        
        polygon_coords = [(coord.longitude, coord.latitude) for coord in polygon]
        shapely_polygon = Polygon(polygon_coords)
        
        intersection = line.intersection(shapely_polygon)
        
        result = []
        if isinstance(intersection, LineString):
            coords = list(intersection.coords)
            if len(coords) >= 2:
                start_coord = Coordinates(latitude=coords[0][1], longitude=coords[0][0])
                end_coord = Coordinates(latitude=coords[-1][1], longitude=coords[-1][0])
                result.append((start_coord, end_coord))
        elif hasattr(intersection, 'geoms'):
            for geom in intersection.geoms:
                if isinstance(geom, LineString):
                    coords = list(geom.coords)
                    if len(coords) >= 2:
                        start_coord = Coordinates(latitude=coords[0][1], longitude=coords[0][0])
                        end_coord = Coordinates(latitude=coords[-1][1], longitude=coords[-1][0])
                        result.append((start_coord, end_coord))
        
        return result
    
    def simplify_polygon(
        self, 
        coordinates: List[Coordinates], 
        tolerance: float = 0.0001
    ) -> List[Coordinates]:
        """Simplify polygon by removing unnecessary vertices."""
        if len(coordinates) <= 3:
            return coordinates
        
        polygon_coords = [(coord.longitude, coord.latitude) for coord in coordinates]
        polygon = Polygon(polygon_coords)
        
        simplified = polygon.simplify(tolerance, preserve_topology=True)
        
        if isinstance(simplified, Polygon):
            exterior_coords = list(simplified.exterior.coords)
            return [
                Coordinates(
                    latitude=lat, 
                    longitude=lon, 
                    altitude=coordinates[0].altitude
                )
                for lon, lat in exterior_coords[:-1]
            ]
        
        return coordinates
    
    # Grid and pattern generation
    
    def generate_grid_points(
        self, 
        bounds: Tuple[float, float, float, float],  # (min_lon, min_lat, max_lon, max_lat)
        spacing: float  # in meters
    ) -> List[Coordinates]:
        """Generate grid points within bounds."""
        min_lon, min_lat, max_lon, max_lat = bounds
        
        # Convert spacing from meters to degrees
        center_lat = (min_lat + max_lat) / 2
        lat_factor = math.cos(math.radians(center_lat))
        
        lat_spacing = spacing / (self.earth_radius * math.pi / 180)
        lon_spacing = spacing / (self.earth_radius * math.pi / 180 * lat_factor)
        
        points = []
        current_lat = min_lat
        
        while current_lat <= max_lat:
            current_lon = min_lon
            while current_lon <= max_lon:
                points.append(Coordinates(latitude=current_lat, longitude=current_lon))
                current_lon += lon_spacing
            current_lat += lat_spacing
        
        return points
    
    def generate_concentric_polygons(
        self, 
        center: Coordinates, 
        radius: float, 
        num_sides: int, 
        num_rings: int
    ) -> List[List[Coordinates]]:
        """Generate concentric polygons around a center point."""
        polygons = []
        
        for ring in range(1, num_rings + 1):
            ring_radius = radius * ring / num_rings
            polygon_points = []
            
            for i in range(num_sides):
                angle = 2 * math.pi * i / num_sides
                point = self.destination_point(center, ring_radius, math.degrees(angle))
                polygon_points.append(point)
            
            polygons.append(polygon_points)
        
        return polygons
    
    # Utility functions
    
    def calculate_polygon_perimeter(self, coordinates: List[Coordinates]) -> float:
        """Calculate polygon perimeter in meters."""
        if len(coordinates) < 2:
            return 0.0
        
        perimeter = 0.0
        for i in range(len(coordinates)):
            next_i = (i + 1) % len(coordinates)
            perimeter += self.haversine_distance(coordinates[i], coordinates[next_i])
        
        return perimeter
    
    def find_polygon_bounds(
        self, 
        coordinates: List[Coordinates]
    ) -> Tuple[float, float, float, float]:
        """Find polygon bounding box (min_lon, min_lat, max_lon, max_lat)."""
        if not coordinates:
            return (0.0, 0.0, 0.0, 0.0)
        
        lats = [coord.latitude for coord in coordinates]
        lons = [coord.longitude for coord in coordinates]
        
        return (min(lons), min(lats), max(lons), max(lats))
    
    def rotate_polygon(
        self, 
        coordinates: List[Coordinates], 
        angle_degrees: float, 
        center: Optional[Coordinates] = None
    ) -> List[Coordinates]:
        """Rotate polygon around center point."""
        if center is None:
            center = self.polygon_centroid(coordinates)
        
        polygon_coords = [(coord.longitude, coord.latitude) for coord in coordinates]
        polygon = Polygon(polygon_coords)
        
        rotated = rotate(
            polygon, 
            angle_degrees, 
            origin=(center.longitude, center.latitude)
        )
        
        if isinstance(rotated, Polygon):
            exterior_coords = list(rotated.exterior.coords)
            return [
                Coordinates(
                    latitude=lat, 
                    longitude=lon, 
                    altitude=coordinates[0].altitude
                )
                for lon, lat in exterior_coords[:-1]
            ]
        
        return coordinates
    
    def scale_polygon(
        self, 
        coordinates: List[Coordinates], 
        scale_factor: float, 
        center: Optional[Coordinates] = None
    ) -> List[Coordinates]:
        """Scale polygon around center point."""
        if center is None:
            center = self.polygon_centroid(coordinates)
        
        polygon_coords = [(coord.longitude, coord.latitude) for coord in coordinates]
        polygon = Polygon(polygon_coords)
        
        scaled = scale(
            polygon, 
            xfact=scale_factor, 
            yfact=scale_factor, 
            origin=(center.longitude, center.latitude)
        )
        
        if isinstance(scaled, Polygon):
            exterior_coords = list(scaled.exterior.coords)
            return [
                Coordinates(
                    latitude=lat, 
                    longitude=lon, 
                    altitude=coordinates[0].altitude
                )
                for lon, lat in exterior_coords[:-1]
            ]
        
        return coordinates
    
    def translate_polygon(
        self, 
        coordinates: List[Coordinates], 
        offset_x: float, 
        offset_y: float
    ) -> List[Coordinates]:
        """Translate polygon by offset in degrees."""
        polygon_coords = [(coord.longitude, coord.latitude) for coord in coordinates]
        polygon = Polygon(polygon_coords)
        
        translated = translate(polygon, xoff=offset_x, yoff=offset_y)
        
        if isinstance(translated, Polygon):
            exterior_coords = list(translated.exterior.coords)
            return [
                Coordinates(
                    latitude=lat, 
                    longitude=lon, 
                    altitude=coordinates[0].altitude
                )
                for lon, lat in exterior_coords[:-1]
            ]
        
        return coordinates
    
    # Advanced calculations
    
    def calculate_optimal_flight_direction(
        self, 
        coordinates: List[Coordinates]
    ) -> float:
        """Calculate optimal flight direction for polygon coverage."""
        if len(coordinates) < 3:
            return 0.0
        
        # Find the longest edge of the polygon
        max_distance = 0.0
        optimal_bearing = 0.0
        
        for i in range(len(coordinates)):
            next_i = (i + 1) % len(coordinates)
            distance = self.haversine_distance(coordinates[i], coordinates[next_i])
            
            if distance > max_distance:
                max_distance = distance
                optimal_bearing = self.calculate_bearing(coordinates[i], coordinates[next_i])
        
        # Return perpendicular direction for optimal coverage
        return (optimal_bearing + 90) % 360
    
    def calculate_minimum_bounding_rectangle(
        self, 
        coordinates: List[Coordinates]
    ) -> Tuple[List[Coordinates], float]:
        """Calculate minimum bounding rectangle and its orientation."""
        polygon_coords = [(coord.longitude, coord.latitude) for coord in coordinates]
        polygon = Polygon(polygon_coords)
        
        # Get minimum rotated rectangle
        min_rect = polygon.minimum_rotated_rectangle
        
        if isinstance(min_rect, Polygon):
            rect_coords = list(min_rect.exterior.coords)
            rect_coordinates = [
                Coordinates(latitude=lat, longitude=lon)
                for lon, lat in rect_coords[:-1]
            ]
            
            # Calculate orientation of the rectangle
            if len(rect_coordinates) >= 2:
                orientation = self.calculate_bearing(rect_coordinates[0], rect_coordinates[1])
            else:
                orientation = 0.0
            
            return rect_coordinates, orientation
        
        return coordinates, 0.0
    
    def validate_polygon(self, coordinates: List[Coordinates]) -> dict:
        """Validate polygon and return validation results."""
        if len(coordinates) < 3:
            return {
                "is_valid": False,
                "errors": ["Polygon must have at least 3 vertices"],
                "warnings": []
            }
        
        polygon_coords = [(coord.longitude, coord.latitude) for coord in coordinates]
        polygon = Polygon(polygon_coords)
        
        errors = []
        warnings = []
        
        if not polygon.is_valid:
            errors.append("Polygon geometry is invalid")
            
            # Check for specific issues
            if polygon.is_empty:
                errors.append("Polygon is empty")
            
            # Check for self-intersection
            if not polygon.is_simple:
                errors.append("Polygon has self-intersections")
        
        # Check for very small area
        area = self.polygon_area(coordinates)
        if area < 100:  # Less than 100 square meters
            warnings.append(f"Polygon area is very small: {area:.1f} m²")
        
        # Check for very long thin polygons
        perimeter = self.calculate_polygon_perimeter(coordinates)
        if area > 0:
            compactness = (4 * math.pi * area) / (perimeter ** 2)
            if compactness < 0.1:
                warnings.append("Polygon is very elongated, may not be suitable for efficient coverage")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "area_m2": area,
            "perimeter_m": perimeter
        }


# Global geometry calculator instance
geometry_calculator = GeometryCalculator()
"""
Coordinate system transformation utilities.
"""

import logging
import math
from typing import Optional, Tuple, List

import numpy as np
from pyproj import Transformer, CRS
from pyproj.exceptions import CRSError

from ..models import Coordinates, CoordinateSystem, HeightMode

logger = logging.getLogger(__name__)


class CoordinateTransformer:
    """Handles coordinate system transformations."""
    
    def __init__(self):
        """Initialize the coordinate transformer."""
        self._transformers = {}
        self._setup_transformers()
    
    def _setup_transformers(self) -> None:
        """Setup common coordinate transformers."""
        try:
            # WGS84 to EGM96 transformer
            self._transformers['wgs84_to_egm96'] = Transformer.from_crs(
                CRS.from_epsg(4979),  # WGS84 3D
                CRS.from_epsg(4326),  # WGS84 2D + EGM96 height
                always_xy=True
            )
            
            # EGM96 to WGS84 transformer
            self._transformers['egm96_to_wgs84'] = Transformer.from_crs(
                CRS.from_epsg(4326),  # WGS84 2D + EGM96 height
                CRS.from_epsg(4979),  # WGS84 3D
                always_xy=True
            )
            
            logger.info("Coordinate transformers initialized successfully")
            
        except CRSError as e:
            logger.error(f"Failed to initialize coordinate transformers: {e}")
            # Fallback to approximate transformations
            self._use_approximate_transforms = True
    
    def transform_coordinates(
        self,
        coordinates: Coordinates,
        source_system: CoordinateSystem,
        target_system: CoordinateSystem,
        reference_point: Optional[Coordinates] = None
    ) -> Coordinates:
        """Transform coordinates between different systems."""
        
        if source_system == target_system:
            return coordinates
        
        # Handle relative coordinate transformations
        if source_system == CoordinateSystem.RELATIVE_TO_START:
            return self._from_relative_coordinates(coordinates, reference_point, target_system)
        
        if target_system == CoordinateSystem.RELATIVE_TO_START:
            return self._to_relative_coordinates(coordinates, reference_point, source_system)
        
        # Handle WGS84 <-> EGM96 transformations
        if source_system == CoordinateSystem.WGS84 and target_system == CoordinateSystem.EGM96:
            return self._wgs84_to_egm96(coordinates)
        
        if source_system == CoordinateSystem.EGM96 and target_system == CoordinateSystem.WGS84:
            return self._egm96_to_wgs84(coordinates)
        
        logger.warning(f"Unsupported transformation: {source_system} -> {target_system}")
        return coordinates
    
    def _wgs84_to_egm96(self, coordinates: Coordinates) -> Coordinates:
        """Transform WGS84 ellipsoid height to EGM96 sea level height."""
        if coordinates.altitude is None:
            return coordinates
        
        try:
            # Use pyproj for accurate transformation
            if 'wgs84_to_egm96' in self._transformers:
                transformer = self._transformers['wgs84_to_egm96']
                lon, lat, alt = transformer.transform(
                    coordinates.longitude,
                    coordinates.latitude,
                    coordinates.altitude
                )
                return Coordinates(latitude=lat, longitude=lon, altitude=alt)
            else:
                # Fallback to approximate transformation
                return self._approximate_wgs84_to_egm96(coordinates)
                
        except Exception as e:
            logger.error(f"WGS84 to EGM96 transformation failed: {e}")
            return self._approximate_wgs84_to_egm96(coordinates)
    
    def _egm96_to_wgs84(self, coordinates: Coordinates) -> Coordinates:
        """Transform EGM96 sea level height to WGS84 ellipsoid height."""
        if coordinates.altitude is None:
            return coordinates
        
        try:
            # Use pyproj for accurate transformation
            if 'egm96_to_wgs84' in self._transformers:
                transformer = self._transformers['egm96_to_wgs84']
                lon, lat, alt = transformer.transform(
                    coordinates.longitude,
                    coordinates.latitude,
                    coordinates.altitude
                )
                return Coordinates(latitude=lat, longitude=lon, altitude=alt)
            else:
                # Fallback to approximate transformation
                return self._approximate_egm96_to_wgs84(coordinates)
                
        except Exception as e:
            logger.error(f"EGM96 to WGS84 transformation failed: {e}")
            return self._approximate_egm96_to_wgs84(coordinates)
    
    def _approximate_wgs84_to_egm96(self, coordinates: Coordinates) -> Coordinates:
        """Approximate WGS84 to EGM96 transformation using geoid height model."""
        if coordinates.altitude is None:
            return coordinates
        
        # Approximate geoid height calculation (simplified)
        geoid_height = self._calculate_approximate_geoid_height(
            coordinates.latitude, coordinates.longitude
        )
        
        # EGM96 height = WGS84 height - geoid height
        egm96_altitude = coordinates.altitude - geoid_height
        
        return Coordinates(
            latitude=coordinates.latitude,
            longitude=coordinates.longitude,
            altitude=egm96_altitude
        )
    
    def _approximate_egm96_to_wgs84(self, coordinates: Coordinates) -> Coordinates:
        """Approximate EGM96 to WGS84 transformation using geoid height model."""
        if coordinates.altitude is None:
            return coordinates
        
        # Approximate geoid height calculation (simplified)
        geoid_height = self._calculate_approximate_geoid_height(
            coordinates.latitude, coordinates.longitude
        )
        
        # WGS84 height = EGM96 height + geoid height
        wgs84_altitude = coordinates.altitude + geoid_height
        
        return Coordinates(
            latitude=coordinates.latitude,
            longitude=coordinates.longitude,
            altitude=wgs84_altitude
        )
    
    def _calculate_approximate_geoid_height(self, latitude: float, longitude: float) -> float:
        """Calculate approximate geoid height using simplified model."""
        # This is a very simplified approximation
        # In practice, you would use EGM96 geoid model data
        
        # Convert to radians
        lat_rad = math.radians(latitude)
        lon_rad = math.radians(longitude)
        
        # Simplified spherical harmonic approximation
        # This is just a rough approximation for demonstration
        geoid_height = (
            30.0 * math.sin(2 * lat_rad) +
            10.0 * math.cos(4 * lat_rad) * math.sin(2 * lon_rad) +
            5.0 * math.sin(6 * lat_rad)
        )
        
        return geoid_height
    
    def _to_relative_coordinates(
        self,
        coordinates: Coordinates,
        reference_point: Optional[Coordinates],
        source_system: CoordinateSystem
    ) -> Coordinates:
        """Convert absolute coordinates to relative coordinates."""
        if reference_point is None:
            raise ValueError("Reference point required for relative coordinate transformation")
        
        # Calculate relative position in meters
        distance, bearing = self._calculate_distance_and_bearing(reference_point, coordinates)
        
        # Convert to local ENU (East-North-Up) coordinates
        east = distance * math.sin(math.radians(bearing))
        north = distance * math.cos(math.radians(bearing))
        up = (coordinates.altitude or 0) - (reference_point.altitude or 0)
        
        return Coordinates(
            latitude=north,  # Store as latitude for consistency
            longitude=east,  # Store as longitude for consistency
            altitude=up
        )
    
    def _from_relative_coordinates(
        self,
        relative_coords: Coordinates,
        reference_point: Optional[Coordinates],
        target_system: CoordinateSystem
    ) -> Coordinates:
        """Convert relative coordinates to absolute coordinates."""
        if reference_point is None:
            raise ValueError("Reference point required for relative coordinate transformation")
        
        # Extract ENU coordinates
        east = relative_coords.longitude  # Stored as longitude
        north = relative_coords.latitude  # Stored as latitude
        up = relative_coords.altitude or 0
        
        # Calculate distance and bearing
        distance = math.sqrt(east**2 + north**2)
        bearing = math.degrees(math.atan2(east, north))
        
        # Convert to absolute coordinates
        absolute_coords = self._calculate_destination_point(reference_point, distance, bearing)
        absolute_coords.altitude = (reference_point.altitude or 0) + up
        
        return absolute_coords
    
    def _calculate_distance_and_bearing(
        self, point1: Coordinates, point2: Coordinates
    ) -> Tuple[float, float]:
        """Calculate distance and bearing between two points."""
        lat1, lon1 = math.radians(point1.latitude), math.radians(point1.longitude)
        lat2, lon2 = math.radians(point2.latitude), math.radians(point2.longitude)
        
        dlon = lon2 - lon1
        
        # Calculate bearing
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = math.degrees(math.atan2(y, x))
        bearing = (bearing + 360) % 360  # Normalize to 0-360
        
        # Calculate distance using Haversine formula
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        distance = 6371000 * c  # Earth radius in meters
        
        return distance, bearing
    
    def _calculate_destination_point(
        self, start_point: Coordinates, distance: float, bearing: float
    ) -> Coordinates:
        """Calculate destination point given start point, distance, and bearing."""
        lat1 = math.radians(start_point.latitude)
        lon1 = math.radians(start_point.longitude)
        bearing_rad = math.radians(bearing)
        
        # Earth radius in meters
        R = 6371000
        
        lat2 = math.asin(
            math.sin(lat1) * math.cos(distance/R) +
            math.cos(lat1) * math.sin(distance/R) * math.cos(bearing_rad)
        )
        
        lon2 = lon1 + math.atan2(
            math.sin(bearing_rad) * math.sin(distance/R) * math.cos(lat1),
            math.cos(distance/R) - math.sin(lat1) * math.sin(lat2)
        )
        
        return Coordinates(
            latitude=math.degrees(lat2),
            longitude=math.degrees(lon2)
        )
    
    def batch_transform(
        self,
        coordinates_list: List[Coordinates],
        source_system: CoordinateSystem,
        target_system: CoordinateSystem,
        reference_point: Optional[Coordinates] = None
    ) -> List[Coordinates]:
        """Transform a batch of coordinates."""
        return [
            self.transform_coordinates(coords, source_system, target_system, reference_point)
            for coords in coordinates_list
        ]
    
    def wgs84_to_gcj02(self, lat: float, lon: float) -> Tuple[float, float]:
        """Convert WGS84 coordinates to GCJ02 (Mars coordinates)."""
        if self._out_of_china(lat, lon):
            return lat, lon
        
        dlat = self._transform_lat(lon - 105.0, lat - 35.0)
        dlon = self._transform_lon(lon - 105.0, lat - 35.0)
        
        radlat = lat / 180.0 * math.pi
        magic = math.sin(radlat)
        magic = 1 - 0.00669342162296594323 * magic * magic
        sqrtmagic = math.sqrt(magic)
        dlat = (dlat * 180.0) / ((6378245.0 * (1 - 0.00669342162296594323)) / (magic * sqrtmagic) * math.pi)
        dlon = (dlon * 180.0) / (6378245.0 / sqrtmagic * math.cos(radlat) * math.pi)
        
        mglat = lat + dlat
        mglon = lon + dlon
        return mglat, mglon
    
    def gcj02_to_wgs84(self, lat: float, lon: float) -> Tuple[float, float]:
        """Convert GCJ02 coordinates to WGS84."""
        if self._out_of_china(lat, lon):
            return lat, lon
        
        dlat = self._transform_lat(lon - 105.0, lat - 35.0)
        dlon = self._transform_lon(lon - 105.0, lat - 35.0)
        
        radlat = lat / 180.0 * math.pi
        magic = math.sin(radlat)
        magic = 1 - 0.00669342162296594323 * magic * magic
        sqrtmagic = math.sqrt(magic)
        dlat = (dlat * 180.0) / ((6378245.0 * (1 - 0.00669342162296594323)) / (magic * sqrtmagic) * math.pi)
        dlon = (dlon * 180.0) / (6378245.0 / sqrtmagic * math.cos(radlat) * math.pi)
        
        mglat = lat - dlat
        mglon = lon - dlon
        return mglat, mglon
    
    def gcj02_to_bd09(self, lat: float, lon: float) -> Tuple[float, float]:
        """Convert GCJ02 coordinates to BD09."""
        z = math.sqrt(lon * lon + lat * lat) + 0.00002 * math.sin(lat * math.pi * 3000.0 / 180.0)
        theta = math.atan2(lat, lon) + 0.000003 * math.cos(lon * math.pi * 3000.0 / 180.0)
        bd_lon = z * math.cos(theta) + 0.0065
        bd_lat = z * math.sin(theta) + 0.006
        return bd_lat, bd_lon
    
    def bd09_to_gcj02(self, lat: float, lon: float) -> Tuple[float, float]:
        """Convert BD09 coordinates to GCJ02."""
        x = lon - 0.0065
        y = lat - 0.006
        z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * math.pi * 3000.0 / 180.0)
        theta = math.atan2(y, x) - 0.000003 * math.cos(x * math.pi * 3000.0 / 180.0)
        gcj_lon = z * math.cos(theta)
        gcj_lat = z * math.sin(theta)
        return gcj_lat, gcj_lon
    
    def _out_of_china(self, lat: float, lon: float) -> bool:
        """Check if coordinates are outside China."""
        return not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271)
    
    def _transform_lat(self, lon: float, lat: float) -> float:
        """Transform latitude for GCJ02 conversion."""
        ret = -100.0 + 2.0 * lon + 3.0 * lat + 0.2 * lat * lat + 0.1 * lon * lat + 0.2 * math.sqrt(abs(lon))
        ret += (20.0 * math.sin(6.0 * lon * math.pi) + 20.0 * math.sin(2.0 * lon * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lat * math.pi) + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(lat / 12.0 * math.pi) + 320 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
        return ret
    
    def _transform_lon(self, lon: float, lat: float) -> float:
        """Transform longitude for GCJ02 conversion."""
        ret = 300.0 + lon + 2.0 * lat + 0.1 * lon * lon + 0.1 * lon * lat + 0.1 * math.sqrt(abs(lon))
        ret += (20.0 * math.sin(6.0 * lon * math.pi) + 20.0 * math.sin(2.0 * lon * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lon * math.pi) + 40.0 * math.sin(lon / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(lon / 12.0 * math.pi) + 300.0 * math.sin(lon / 30.0 * math.pi)) * 2.0 / 3.0
        return ret

    def validate_coordinate_precision(self, coordinates: Coordinates) -> dict:
        """Validate coordinate precision and provide recommendations."""
        warnings = []
        
        # Check decimal precision
        lat_precision = len(str(coordinates.latitude).split('.')[-1]) if '.' in str(coordinates.latitude) else 0
        lon_precision = len(str(coordinates.longitude).split('.')[-1]) if '.' in str(coordinates.longitude) else 0
        
        if lat_precision < 6:
            warnings.append(f"Latitude precision ({lat_precision} decimals) may be insufficient for accurate positioning")
        
        if lon_precision < 6:
            warnings.append(f"Longitude precision ({lon_precision} decimals) may be insufficient for accurate positioning")
        
        # Check for reasonable coordinate ranges
        if abs(coordinates.latitude) > 85:
            warnings.append("Latitude near poles may have transformation accuracy issues")
        
        if coordinates.altitude is not None:
            if coordinates.altitude < -500 or coordinates.altitude > 10000:
                warnings.append("Altitude outside typical flight range")
        
        return {
            "is_valid": len(warnings) == 0,
            "warnings": warnings,
            "precision": {
                "latitude_decimals": lat_precision,
                "longitude_decimals": lon_precision
            }
        }


# Global transformer instance
coordinate_transformer = CoordinateTransformer()
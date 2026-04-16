"""
Coordinate system models and transformations.
"""

from enum import Enum
from typing import Optional, Tuple

from pydantic import BaseModel, Field, validator


class CoordinateSystem(str, Enum):
    """Supported coordinate systems."""
    WGS84 = "WGS84"
    EGM96 = "EGM96"
    RELATIVE_TO_START = "relativeToStartPoint"


class HeightMode(str, Enum):
    """Height reference modes."""
    WGS84 = "WGS84"  # Ellipsoid height
    EGM96 = "EGM96"  # Sea level height
    RELATIVE_TO_START = "relativeToStartPoint"  # Relative to takeoff point
    AGL = "AGL"  # Above ground level


class Coordinates(BaseModel):
    """Geographic coordinates with validation."""
    
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    
    @validator('latitude')
    def validate_latitude(cls, v):
        """Validate latitude range."""
        if not -90 <= v <= 90:
            raise ValueError(f"Latitude must be between -90 and 90 degrees, got {v}")
        return v
    
    @validator('longitude')
    def validate_longitude(cls, v):
        """Validate longitude range."""
        if not -180 <= v <= 180:
            raise ValueError(f"Longitude must be between -180 and 180 degrees, got {v}")
        return v
    
    def to_tuple(self) -> Tuple[float, float, Optional[float]]:
        """Convert to tuple format (lat, lon, alt)."""
        return (self.latitude, self.longitude, self.altitude)
    
    def to_kml_coordinates(self) -> str:
        """Convert to KML coordinate format (lon,lat,alt)."""
        if self.altitude is not None:
            return f"{self.longitude},{self.latitude},{self.altitude}"
        else:
            return f"{self.longitude},{self.latitude}"


class CoordinateTransform(BaseModel):
    """Coordinate transformation parameters."""
    
    source_system: CoordinateSystem = Field(..., description="Source coordinate system")
    target_system: CoordinateSystem = Field(..., description="Target coordinate system")
    reference_point: Optional[Coordinates] = Field(None, description="Reference point for relative coordinates")
    
    def transform(self, coordinates: Coordinates) -> Coordinates:
        """Transform coordinates between systems."""
        from ..utils.coordinate_transforms import coordinate_transformer
        return coordinate_transformer.transform_coordinates(
            coordinates, self.source_system, self.target_system, self.reference_point
        )


class BoundingBox(BaseModel):
    """Geographic bounding box."""
    
    min_latitude: float = Field(..., ge=-90, le=90)
    max_latitude: float = Field(..., ge=-90, le=90)
    min_longitude: float = Field(..., ge=-180, le=180)
    max_longitude: float = Field(..., ge=-180, le=180)
    
    @validator('max_latitude')
    def validate_latitude_order(cls, v, values):
        """Ensure max_latitude > min_latitude."""
        if 'min_latitude' in values and v <= values['min_latitude']:
            raise ValueError("max_latitude must be greater than min_latitude")
        return v
    
    @validator('max_longitude')
    def validate_longitude_order(cls, v, values):
        """Ensure max_longitude > min_longitude."""
        if 'min_longitude' in values and v <= values['min_longitude']:
            raise ValueError("max_longitude must be greater than min_longitude")
        return v
    
    def contains(self, coordinates: Coordinates) -> bool:
        """Check if coordinates are within the bounding box."""
        return (
            self.min_latitude <= coordinates.latitude <= self.max_latitude and
            self.min_longitude <= coordinates.longitude <= self.max_longitude
        )
    
    def center(self) -> Coordinates:
        """Get the center point of the bounding box."""
        return Coordinates(
            latitude=(self.min_latitude + self.max_latitude) / 2,
            longitude=(self.min_longitude + self.max_longitude) / 2
        )
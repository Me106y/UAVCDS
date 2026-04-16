"""
Mapping mission MCP tools.
"""

import math
from typing import Any, Dict, List, Tuple, Optional

import numpy as np
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import transform
from shapely.affinity import rotate
from mcp.types import Tool
from pydantic import BaseModel, Field, ValidationError, validator

from .base import BaseTool, ValidationMixin
from ..models import (
    Coordinates,
    Waypoint,
    FlightPath,
    Action,
    ActionGroup,
    ActionTrigger,
    ActionType,
    ActionTriggerType,
    HeightMode,
    WaypointTurnMode,
    AircraftModel,
)
from ..config import settings


class SurveyAreaPoint(BaseModel):
    """Survey area vertex point."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class MappingMissionInput(BaseModel):
    """Input schema for mapping mission planning."""
    survey_area: List[SurveyAreaPoint] = Field(..., min_items=3, description="Polygon vertices defining survey area")
    flight_height: float = Field(default=100.0, ge=10, le=1500, description="Flight height in meters")
    overlap_rate: float = Field(default=80.0, ge=50, le=95, description="Photo overlap percentage")
    sidelap_rate: float = Field(default=70.0, ge=30, le=90, description="Photo sidelap percentage")
    flight_direction: float = Field(default=0.0, ge=0, le=360, description="Flight direction in degrees")
    flight_speed: float = Field(default=5.0, ge=1, le=15, description="Flight speed in m/s")
    aircraft_type: str = Field(default="M30", description="Aircraft model")
    margin: float = Field(default=20.0, ge=0, le=100, description="Survey area margin in meters")
    shoot_mode: str = Field(default="time", description="Photo shooting mode (time/distance)")
    gimbal_pitch: float = Field(default=-90.0, ge=-120, le=45, description="Gimbal pitch angle")
    enable_terrain_following: bool = Field(default=False, description="Enable terrain following")
    
    @validator('survey_area')
    def validate_survey_area(cls, v):
        """Validate survey area forms a valid polygon."""
        if len(v) < 3:
            raise ValueError("Survey area must have at least 3 vertices")
        return v


class FlightLineGenerator:
    """Generates parallel flight lines for mapping missions."""
    
    def __init__(self):
        """Initialize the flight line generator."""
        self.earth_radius = 6371000  # Earth radius in meters
    
    def generate_flight_lines(
        self,
        survey_polygon: Polygon,
        flight_direction: float,
        line_spacing: float,
        margin: float = 0.0
    ) -> List[LineString]:
        """Generate parallel flight lines covering the survey area."""
        
        # Expand polygon by margin if specified
        if margin > 0:
            # Convert margin from meters to degrees (approximate)
            margin_degrees = margin / (self.earth_radius * math.pi / 180)
            survey_polygon = survey_polygon.buffer(margin_degrees)
        
        # Get polygon bounds
        minx, miny, maxx, maxy = survey_polygon.bounds
        
        # Calculate the polygon's center for rotation
        center_x = (minx + maxx) / 2
        center_y = (miny + maxy) / 2
        
        # Rotate polygon to align with flight direction
        # Flight direction 0° = North, 90° = East
        rotation_angle = -(flight_direction - 90)  # Convert to standard math angle
        rotated_polygon = rotate(survey_polygon, rotation_angle, origin=(center_x, center_y))
        
        # Get bounds of rotated polygon
        rot_minx, rot_miny, rot_maxx, rot_maxy = rotated_polygon.bounds
        
        # Convert line spacing from meters to degrees (approximate)
        spacing_degrees = line_spacing / (self.earth_radius * math.pi / 180 * math.cos(math.radians(center_y)))
        
        # Generate parallel lines
        flight_lines = []
        current_x = rot_minx
        line_index = 0
        
        while current_x <= rot_maxx:
            # Create vertical line at current_x
            line = LineString([(current_x, rot_miny - spacing_degrees), 
                              (current_x, rot_maxy + spacing_degrees)])
            
            # Intersect with rotated polygon
            intersection = line.intersection(rotated_polygon)
            
            if intersection and not intersection.is_empty:
                if hasattr(intersection, 'geoms'):
                    # Multiple intersections
                    for geom in intersection.geoms:
                        if isinstance(geom, LineString):
                            # Rotate back to original orientation
                            original_line = rotate(geom, -rotation_angle, origin=(center_x, center_y))
                            flight_lines.append(original_line)
                elif isinstance(intersection, LineString):
                    # Single intersection
                    original_line = rotate(intersection, -rotation_angle, origin=(center_x, center_y))
                    flight_lines.append(original_line)
            
            current_x += spacing_degrees
            line_index += 1
        
        # Optimize flight line order (boustrophedon pattern)
        return self._optimize_flight_line_order(flight_lines)
    
    def _optimize_flight_line_order(self, flight_lines: List[LineString]) -> List[LineString]:
        """Optimize flight line order for efficient flight pattern (boustrophedon)."""
        if not flight_lines:
            return flight_lines
        
        optimized_lines = []
        remaining_lines = flight_lines.copy()
        
        # Start with the leftmost line
        current_line = min(remaining_lines, key=lambda line: line.coords[0][0])
        remaining_lines.remove(current_line)
        optimized_lines.append(current_line)
        
        # Alternate direction for each subsequent line
        reverse_next = True
        
        while remaining_lines:
            # Find the nearest line to the end of current line
            current_end = Point(current_line.coords[-1])
            
            nearest_line = min(remaining_lines, 
                             key=lambda line: min(
                                 current_end.distance(Point(line.coords[0])),
                                 current_end.distance(Point(line.coords[-1]))
                             ))
            
            remaining_lines.remove(nearest_line)
            
            # Reverse line direction if needed for boustrophedon pattern
            if reverse_next:
                # Reverse the line coordinates
                reversed_coords = list(reversed(nearest_line.coords))
                nearest_line = LineString(reversed_coords)
            
            optimized_lines.append(nearest_line)
            current_line = nearest_line
            reverse_next = not reverse_next
        
        return optimized_lines
    
    def calculate_line_spacing(
        self,
        flight_height: float,
        camera_specs: Dict[str, float],
        sidelap_percentage: float
    ) -> float:
        """Calculate required line spacing based on camera specs and sidelap."""
        # Default camera specs for common DJI aircraft
        default_specs = {
            "sensor_width": 23.5,  # mm
            "sensor_height": 15.6,  # mm
            "focal_length": 24.0,  # mm
            "image_width": 5472,   # pixels
            "image_height": 3648   # pixels
        }
        
        specs = {**default_specs, **camera_specs}
        
        # Calculate ground coverage width
        ground_width = (specs["sensor_width"] * flight_height) / specs["focal_length"]
        
        # Calculate line spacing based on sidelap
        sidelap_factor = (100 - sidelap_percentage) / 100
        line_spacing = ground_width * sidelap_factor
        
        return line_spacing
    
    def calculate_photo_interval(
        self,
        flight_speed: float,
        flight_height: float,
        camera_specs: Dict[str, float],
        overlap_percentage: float
    ) -> float:
        """Calculate photo interval for time-based shooting."""
        # Default camera specs
        default_specs = {
            "sensor_width": 23.5,  # mm
            "sensor_height": 15.6,  # mm
            "focal_length": 24.0,  # mm
        }
        
        specs = {**default_specs, **camera_specs}
        
        # Calculate ground coverage length
        ground_length = (specs["sensor_height"] * flight_height) / specs["focal_length"]
        
        # Calculate photo spacing based on overlap
        overlap_factor = (100 - overlap_percentage) / 100
        photo_spacing = ground_length * overlap_factor
        
        # Calculate time interval
        photo_interval = photo_spacing / flight_speed
        
        return max(photo_interval, 1.0)  # Minimum 1 second interval


class MappingMissionTool(BaseTool, ValidationMixin):
    """Tool for planning mapping missions."""
    
    def __init__(self):
        """Initialize the mapping mission tool."""
        super().__init__()
        self.flight_line_generator = FlightLineGenerator()
    
    def get_tool_definition(self) -> Tool:
        """Get the MCP tool definition."""
        return Tool(
            name="plan_mapping_mission",
            description="Plan an automated mapping survey mission with parallel flight lines",
            inputSchema={
                "type": "object",
                "properties": {
                    "survey_area": {
                        "type": "array",
                        "description": "Polygon coordinates defining the survey area",
                        "minItems": 3,
                        "items": {
                            "type": "object",
                            "properties": {
                                "latitude": {"type": "number", "minimum": -90, "maximum": 90},
                                "longitude": {"type": "number", "minimum": -180, "maximum": 180}
                            },
                            "required": ["latitude", "longitude"]
                        }
                    },
                    "flight_height": {
                        "type": "number",
                        "description": "Flight height in meters",
                        "minimum": 10,
                        "maximum": 1500,
                        "default": 100.0
                    },
                    "overlap_rate": {
                        "type": "number",
                        "description": "Photo overlap percentage (50-95)",
                        "minimum": 50,
                        "maximum": 95,
                        "default": 80.0
                    },
                    "sidelap_rate": {
                        "type": "number",
                        "description": "Photo sidelap percentage (30-90)",
                        "minimum": 30,
                        "maximum": 90,
                        "default": 70.0
                    },
                    "flight_direction": {
                        "type": "number",
                        "description": "Flight direction in degrees (0-360)",
                        "minimum": 0,
                        "maximum": 360,
                        "default": 0.0
                    },
                    "flight_speed": {
                        "type": "number",
                        "description": "Flight speed in m/s",
                        "minimum": 1,
                        "maximum": 15,
                        "default": 5.0
                    },
                    "aircraft_type": {
                        "type": "string",
                        "description": "Aircraft model",
                        "enum": ["M300_RTK", "M350_RTK", "M30", "M30T", "M3E", "M3T", "M3M", "M3D", "M3TD"],
                        "default": "M30"
                    },
                    "margin": {
                        "type": "number",
                        "description": "Survey area margin in meters",
                        "minimum": 0,
                        "maximum": 100,
                        "default": 20.0
                    },
                    "shoot_mode": {
                        "type": "string",
                        "description": "Photo shooting mode",
                        "enum": ["time", "distance"],
                        "default": "time"
                    },
                    "gimbal_pitch": {
                        "type": "number",
                        "description": "Gimbal pitch angle in degrees",
                        "minimum": -120,
                        "maximum": 45,
                        "default": -90.0
                    },
                    "enable_terrain_following": {
                        "type": "boolean",
                        "description": "Enable terrain following",
                        "default": False
                    }
                },
                "required": ["survey_area"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute mapping mission planning."""
        try:
            # Validate input arguments
            mission_input = MappingMissionInput(**arguments)
            
            self.logger.info(f"Planning mapping mission for area with {len(mission_input.survey_area)} vertices")
            
            # Create survey polygon
            survey_polygon = self._create_survey_polygon(mission_input.survey_area)
            
            # Validate polygon
            if not survey_polygon.is_valid:
                raise ValueError("Invalid survey area polygon")
            
            # Get camera specifications for aircraft
            camera_specs = self._get_camera_specs(mission_input.aircraft_type)
            
            # Calculate line spacing
            line_spacing = self.flight_line_generator.calculate_line_spacing(
                mission_input.flight_height,
                camera_specs,
                mission_input.sidelap_rate
            )
            
            # Generate flight lines
            flight_lines = self.flight_line_generator.generate_flight_lines(
                survey_polygon,
                mission_input.flight_direction,
                line_spacing,
                mission_input.margin
            )
            
            if not flight_lines:
                raise ValueError("No flight lines generated for the survey area")
            
            # Convert flight lines to waypoints
            waypoints = self._flight_lines_to_waypoints(
                flight_lines,
                mission_input.flight_height,
                mission_input.flight_speed
            )
            
            # Add photo actions
            waypoints = self._add_photo_actions(
                waypoints,
                mission_input,
                camera_specs
            )
            
            # Create flight path
            flight_path = FlightPath(
                waypoints=waypoints,
                global_speed=mission_input.flight_speed,
                global_height=mission_input.flight_height,
                height_mode=HeightMode.EGM96,
                global_turn_mode=WaypointTurnMode.TO_POINT_STOP_DISCONTINUITY
            )
            
            # Calculate mission statistics
            stats = self._calculate_mission_statistics(
                flight_path,
                survey_polygon,
                mission_input,
                camera_specs
            )
            
            # Prepare response
            response_data = {
                "flight_path": {
                    "waypoint_count": len(waypoints),
                    "flight_lines": len(flight_lines),
                    "total_distance": stats["total_distance"],
                    "estimated_flight_time": stats["estimated_flight_time"]
                },
                "survey_configuration": {
                    "area_hectares": stats["survey_area_hectares"],
                    "flight_height": mission_input.flight_height,
                    "overlap_rate": mission_input.overlap_rate,
                    "sidelap_rate": mission_input.sidelap_rate,
                    "flight_direction": mission_input.flight_direction,
                    "line_spacing": round(line_spacing, 2)
                },
                "photo_configuration": {
                    "shoot_mode": mission_input.shoot_mode,
                    "photo_interval": stats["photo_interval"],
                    "estimated_photos": stats["estimated_photos"],
                    "ground_resolution": stats["ground_resolution"]
                },
                "statistics": stats
            }
            
            return self.format_success_response(
                f"Mapping mission planned successfully with {len(flight_lines)} flight lines and {len(waypoints)} waypoints",
                response_data
            )
            
        except ValidationError as e:
            self.logger.error(f"Validation error in mapping mission planning: {e}")
            return self.format_error_response(f"Invalid input parameters: {e}")
        
        except ValueError as e:
            self.logger.error(f"Value error in mapping mission planning: {e}")
            return self.format_error_response(str(e))
        
        except Exception as e:
            self.logger.error(f"Unexpected error in mapping mission planning: {e}", exc_info=True)
            return self.format_error_response(f"Mapping mission planning failed: {e}")
    
    def _create_survey_polygon(self, survey_area: List[SurveyAreaPoint]) -> Polygon:
        """Create a Shapely polygon from survey area points."""
        coordinates = [(point.longitude, point.latitude) for point in survey_area]
        
        # Ensure polygon is closed
        if coordinates[0] != coordinates[-1]:
            coordinates.append(coordinates[0])
        
        return Polygon(coordinates)
    
    def _get_camera_specs(self, aircraft_type: str) -> Dict[str, float]:
        """Get camera specifications for aircraft type."""
        camera_specs = {
            "M30": {
                "sensor_width": 23.5,
                "sensor_height": 15.6,
                "focal_length": 24.0,
                "image_width": 5472,
                "image_height": 3648
            },
            "M30T": {
                "sensor_width": 23.5,
                "sensor_height": 15.6,
                "focal_length": 24.0,
                "image_width": 5472,
                "image_height": 3648
            },
            "M3E": {
                "sensor_width": 17.3,
                "sensor_height": 13.0,
                "focal_length": 24.0,
                "image_width": 5280,
                "image_height": 3956
            },
            "M300_RTK": {
                "sensor_width": 35.9,
                "sensor_height": 24.0,
                "focal_length": 35.0,
                "image_width": 8192,
                "image_height": 5460
            }
        }
        
        return camera_specs.get(aircraft_type, camera_specs["M30"])
    
    def _flight_lines_to_waypoints(
        self,
        flight_lines: List[LineString],
        flight_height: float,
        flight_speed: float
    ) -> List[Waypoint]:
        """Convert flight lines to waypoints."""
        waypoints = []
        waypoint_index = 0
        
        for line in flight_lines:
            # Add waypoints for line start and end
            for coord in line.coords:
                longitude, latitude = coord
                
                coordinates = Coordinates(
                    latitude=latitude,
                    longitude=longitude,
                    altitude=flight_height
                )
                
                waypoint = Waypoint(
                    index=waypoint_index,
                    coordinates=coordinates,
                    speed=flight_speed,
                    use_global_height=True,
                    use_global_speed=True
                )
                
                waypoints.append(waypoint)
                waypoint_index += 1
        
        return waypoints
    
    def _add_photo_actions(
        self,
        waypoints: List[Waypoint],
        mission_input: MappingMissionInput,
        camera_specs: Dict[str, float]
    ) -> List[Waypoint]:
        """Add photo capture actions to waypoints."""
        if mission_input.shoot_mode == "time":
            # Calculate photo interval
            photo_interval = self.flight_line_generator.calculate_photo_interval(
                mission_input.flight_speed,
                mission_input.flight_height,
                camera_specs,
                mission_input.overlap_rate
            )
            
            # Add time-based photo action to first waypoint of each flight line
            line_start_indices = list(range(0, len(waypoints), 2))  # Every other waypoint is line start
            
            for i, waypoint_idx in enumerate(line_start_indices):
                if waypoint_idx < len(waypoints):
                    waypoint = waypoints[waypoint_idx]
                    
                    # Create photo action
                    photo_action = Action(
                        action_id=0,
                        action_type=ActionType.TAKE_PHOTO,
                        parameters={
                            "suffix": f"line_{i}",
                            "payload_position": 0,
                            "use_global_lens": 1
                        }
                    )
                    
                    # Create action group with time trigger
                    action_group = ActionGroup(
                        group_id=0,
                        start_index=waypoint_idx,
                        end_index=waypoint_idx + 1 if waypoint_idx + 1 < len(waypoints) else waypoint_idx,
                        trigger=ActionTrigger(
                            trigger_type=ActionTriggerType.MULTIPLE_TIMING,
                            trigger_param=photo_interval
                        ),
                        actions=[photo_action]
                    )
                    
                    waypoint.action_groups = [action_group]
        
        return waypoints
    
    def _calculate_mission_statistics(
        self,
        flight_path: FlightPath,
        survey_polygon: Polygon,
        mission_input: MappingMissionInput,
        camera_specs: Dict[str, float]
    ) -> Dict[str, Any]:
        """Calculate mission statistics."""
        # Calculate survey area in hectares
        # Convert from square degrees to square meters (approximate)
        area_sq_degrees = survey_polygon.area
        area_sq_meters = area_sq_degrees * (111000 ** 2)  # Rough conversion
        area_hectares = area_sq_meters / 10000
        
        # Calculate total flight distance
        total_distance = 0.0
        for i in range(len(flight_path.waypoints) - 1):
            wp1 = flight_path.waypoints[i]
            wp2 = flight_path.waypoints[i + 1]
            
            # Use Haversine formula for distance
            distance = self._calculate_distance(wp1.coordinates, wp2.coordinates)
            total_distance += distance
        
        # Calculate flight time
        estimated_flight_time = total_distance / mission_input.flight_speed
        
        # Calculate photo interval and count
        photo_interval = self.flight_line_generator.calculate_photo_interval(
            mission_input.flight_speed,
            mission_input.flight_height,
            camera_specs,
            mission_input.overlap_rate
        )
        
        estimated_photos = int(estimated_flight_time / photo_interval) if photo_interval > 0 else 0
        
        # Calculate ground resolution
        ground_resolution = (camera_specs["sensor_width"] * mission_input.flight_height) / (
            camera_specs["focal_length"] * camera_specs["image_width"]
        ) * 1000  # Convert to mm/pixel
        
        return {
            "survey_area_hectares": round(area_hectares, 2),
            "total_distance": round(total_distance, 2),
            "estimated_flight_time": round(estimated_flight_time, 1),
            "photo_interval": round(photo_interval, 2),
            "estimated_photos": estimated_photos,
            "ground_resolution": round(ground_resolution, 2),
            "waypoint_count": len(flight_path.waypoints)
        }
    
    def _calculate_distance(self, coord1: Coordinates, coord2: Coordinates) -> float:
        """Calculate distance between two coordinates using Haversine formula."""
        lat1, lon1 = math.radians(coord1.latitude), math.radians(coord1.longitude)
        lat2, lon2 = math.radians(coord2.latitude), math.radians(coord2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return 6371000 * c  # Earth radius in meters
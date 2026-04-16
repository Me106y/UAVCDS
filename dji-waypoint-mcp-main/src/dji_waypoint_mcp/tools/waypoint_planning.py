"""
Waypoint planning MCP tools.
"""

import math
from typing import Any, Dict, List, Optional

from mcp.types import Tool
from pydantic import BaseModel, Field, ValidationError

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
    HeadingMode,
    WaypointTurnMode,
    HeightMode,
    AircraftModel,
    PayloadModel,
)
from ..config import settings


class WaypointInput(BaseModel):
    """Input schema for waypoint data."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: float = Field(..., description="Altitude in meters")
    speed: Optional[float] = Field(None, ge=1, le=15, description="Speed to this waypoint (m/s)")
    heading_angle: Optional[float] = Field(None, ge=-180, le=180, description="Heading angle in degrees")
    gimbal_pitch: Optional[float] = Field(None, ge=-120, le=45, description="Gimbal pitch angle")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Actions to perform at waypoint")


class WaypointMissionInput(BaseModel):
    """Input schema for waypoint mission planning."""
    waypoints: List[WaypointInput] = Field(..., min_items=2, description="List of waypoints")
    aircraft_type: str = Field(default="M30", description="Aircraft model")
    flight_speed: float = Field(default=5.0, ge=1, le=15, description="Global flight speed (m/s)")
    flight_height: Optional[float] = Field(None, description="Global flight height (m)")
    height_mode: str = Field(default="EGM96", description="Height reference mode")
    heading_mode: str = Field(default="followWayline", description="Aircraft heading mode")
    turn_mode: str = Field(default="toPointAndStopWithDiscontinuityCurvature", description="Waypoint turn mode")
    takeoff_point: Optional[Dict[str, float]] = Field(None, description="Takeoff reference point")


class WaypointPlanningTool(BaseTool, ValidationMixin):
    """Tool for planning waypoint missions."""
    
    def get_tool_definition(self) -> Tool:
        """Get the MCP tool definition."""
        return Tool(
            name="plan_waypoint_mission",
            description="Plan a custom waypoint flight mission with detailed configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "waypoints": {
                        "type": "array",
                        "description": "List of waypoints with coordinates and actions",
                        "minItems": 2,
                        "items": {
                            "type": "object",
                            "properties": {
                                "latitude": {"type": "number", "minimum": -90, "maximum": 90},
                                "longitude": {"type": "number", "minimum": -180, "maximum": 180},
                                "altitude": {"type": "number", "description": "Altitude in meters"},
                                "speed": {"type": "number", "minimum": 1, "maximum": 15, "description": "Speed to waypoint (m/s)"},
                                "heading_angle": {"type": "number", "minimum": -180, "maximum": 180},
                                "gimbal_pitch": {"type": "number", "minimum": -120, "maximum": 45},
                                "actions": {"type": "array", "items": {"type": "object"}, "default": []}
                            },
                            "required": ["latitude", "longitude", "altitude"]
                        }
                    },
                    "aircraft_type": {
                        "type": "string",
                        "description": "Aircraft model",
                        "enum": ["M300_RTK", "M350_RTK", "M30", "M30T", "M3E", "M3T", "M3M", "M3D", "M3TD"],
                        "default": "M30"
                    },
                    "flight_speed": {
                        "type": "number",
                        "description": "Global flight speed in m/s",
                        "minimum": 1,
                        "maximum": 15,
                        "default": 5.0
                    },
                    "flight_height": {
                        "type": "number",
                        "description": "Global flight height in meters",
                        "minimum": 1,
                        "maximum": 1500
                    },
                    "height_mode": {
                        "type": "string",
                        "description": "Height reference mode",
                        "enum": ["WGS84", "EGM96", "relativeToStartPoint"],
                        "default": "EGM96"
                    },
                    "heading_mode": {
                        "type": "string",
                        "description": "Aircraft heading mode",
                        "enum": ["followWayline", "manually", "fixed", "smoothTransition", "towardPOI"],
                        "default": "followWayline"
                    },
                    "turn_mode": {
                        "type": "string",
                        "description": "Waypoint turn mode",
                        "enum": [
                            "coordinateTurn",
                            "toPointAndStopWithDiscontinuityCurvature",
                            "toPointAndStopWithContinuityCurvature",
                            "toPointAndPassWithContinuityCurvature"
                        ],
                        "default": "toPointAndStopWithDiscontinuityCurvature"
                    },
                    "takeoff_point": {
                        "type": "object",
                        "description": "Reference takeoff point",
                        "properties": {
                            "latitude": {"type": "number", "minimum": -90, "maximum": 90},
                            "longitude": {"type": "number", "minimum": -180, "maximum": 180},
                            "altitude": {"type": "number"}
                        }
                    }
                },
                "required": ["waypoints"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute waypoint mission planning."""
        try:
            # Validate input arguments
            mission_input = WaypointMissionInput(**arguments)
            
            self.logger.info(f"Planning waypoint mission with {len(mission_input.waypoints)} waypoints")
            
            # Validate waypoint count
            if len(mission_input.waypoints) > settings.max_waypoints:
                raise ValueError(f"Too many waypoints: {len(mission_input.waypoints)}. Maximum allowed: {settings.max_waypoints}")
            
            # Create waypoint objects
            waypoints = []
            for i, wp_input in enumerate(mission_input.waypoints):
                # Validate coordinates
                self.validate_coordinates(wp_input.latitude, wp_input.longitude)
                
                # Create coordinates
                coords = Coordinates(
                    latitude=wp_input.latitude,
                    longitude=wp_input.longitude,
                    altitude=wp_input.altitude
                )
                
                # Create waypoint
                waypoint = Waypoint(
                    index=i,
                    coordinates=coords,
                    speed=wp_input.speed,
                    gimbal_pitch_angle=wp_input.gimbal_pitch,
                    use_global_height=mission_input.flight_height is not None,
                    use_global_speed=wp_input.speed is None
                )
                
                # Add actions if specified
                if wp_input.actions:
                    action_groups = self._create_action_groups(wp_input.actions, i)
                    waypoint.action_groups = action_groups
                
                waypoints.append(waypoint)
            
            # Create flight path
            flight_path = FlightPath(
                waypoints=waypoints,
                global_speed=mission_input.flight_speed,
                global_height=mission_input.flight_height,
                height_mode=HeightMode(mission_input.height_mode),
                global_turn_mode=WaypointTurnMode(mission_input.turn_mode)
            )
            
            # Perform safety validations
            safety_results = self._validate_flight_safety(flight_path)
            
            # Calculate flight statistics
            stats = self._calculate_flight_statistics(flight_path)
            
            # Prepare response
            response_data = {
                "flight_path": {
                    "waypoint_count": len(waypoints),
                    "total_distance": stats["total_distance"],
                    "estimated_flight_time": stats["estimated_flight_time"],
                    "bounding_box": self._get_bounding_box_dict(flight_path.get_bounding_box())
                },
                "configuration": {
                    "aircraft_type": mission_input.aircraft_type,
                    "flight_speed": mission_input.flight_speed,
                    "height_mode": mission_input.height_mode,
                    "heading_mode": mission_input.heading_mode,
                    "turn_mode": mission_input.turn_mode
                },
                "safety_validation": safety_results,
                "statistics": stats
            }
            
            return self.format_success_response(
                f"Waypoint mission planned successfully with {len(waypoints)} waypoints",
                response_data
            )
            
        except ValidationError as e:
            self.logger.error(f"Validation error in waypoint planning: {e}")
            return self.format_error_response(f"Invalid input parameters: {e}")
        
        except ValueError as e:
            self.logger.error(f"Value error in waypoint planning: {e}")
            return self.format_error_response(str(e))
        
        except Exception as e:
            self.logger.error(f"Unexpected error in waypoint planning: {e}", exc_info=True)
            return self.format_error_response(f"Planning failed: {e}")
    
    def _create_action_groups(self, actions_data: List[Dict[str, Any]], waypoint_index: int) -> List[ActionGroup]:
        """Create action groups from input data."""
        action_groups = []
        
        if not actions_data:
            return action_groups
        
        # Create a single action group for all actions at this waypoint
        actions = []
        for i, action_data in enumerate(actions_data):
            action_type = action_data.get("type", "takePhoto")
            
            # Validate action type
            try:
                action_type_enum = ActionType(action_type)
            except ValueError:
                self.logger.warning(f"Unknown action type: {action_type}, defaulting to takePhoto")
                action_type_enum = ActionType.TAKE_PHOTO
            
            action = Action(
                action_id=i,
                action_type=action_type_enum,
                parameters=action_data.get("parameters", {})
            )
            actions.append(action)
        
        if actions:
            action_group = ActionGroup(
                group_id=0,
                start_index=waypoint_index,
                end_index=waypoint_index,
                trigger=ActionTrigger(trigger_type=ActionTriggerType.REACH_POINT),
                actions=actions
            )
            action_groups.append(action_group)
        
        return action_groups
    
    def _validate_flight_safety(self, flight_path: FlightPath) -> Dict[str, Any]:
        """Validate flight safety parameters."""
        warnings = []
        errors = []
        
        # Check flight distance
        total_distance = self._calculate_total_distance(flight_path)
        if total_distance > settings.max_flight_distance:
            errors.append(f"Flight distance ({total_distance:.1f}m) exceeds maximum ({settings.max_flight_distance}m)")
        
        # Check flight height
        max_altitude = max(wp.coordinates.altitude or 0 for wp in flight_path.waypoints)
        if max_altitude > settings.max_flight_height:
            errors.append(f"Flight height ({max_altitude:.1f}m) exceeds maximum ({settings.max_flight_height}m)")
        
        # Check waypoint spacing
        for i in range(len(flight_path.waypoints) - 1):
            distance = self._calculate_distance_between_waypoints(
                flight_path.waypoints[i], 
                flight_path.waypoints[i + 1]
            )
            if distance < 5.0:  # Minimum 5m between waypoints
                warnings.append(f"Short distance between waypoints {i} and {i+1}: {distance:.1f}m")
        
        return {
            "is_valid": len(errors) == 0,
            "warnings": warnings,
            "errors": errors
        }
    
    def _calculate_flight_statistics(self, flight_path: FlightPath) -> Dict[str, Any]:
        """Calculate flight statistics."""
        total_distance = self._calculate_total_distance(flight_path)
        estimated_time = total_distance / flight_path.global_speed
        
        # Calculate altitude statistics
        altitudes = [wp.coordinates.altitude or 0 for wp in flight_path.waypoints]
        
        return {
            "total_distance": round(total_distance, 2),
            "estimated_flight_time": round(estimated_time, 1),
            "waypoint_count": len(flight_path.waypoints),
            "min_altitude": min(altitudes),
            "max_altitude": max(altitudes),
            "avg_altitude": round(sum(altitudes) / len(altitudes), 2),
            "action_count": sum(len(wp.action_groups) for wp in flight_path.waypoints)
        }
    
    def _calculate_total_distance(self, flight_path: FlightPath) -> float:
        """Calculate total flight path distance."""
        total_distance = 0.0
        
        for i in range(len(flight_path.waypoints) - 1):
            distance = self._calculate_distance_between_waypoints(
                flight_path.waypoints[i],
                flight_path.waypoints[i + 1]
            )
            total_distance += distance
        
        return total_distance
    
    def _calculate_distance_between_waypoints(self, wp1: Waypoint, wp2: Waypoint) -> float:
        """Calculate distance between two waypoints using Haversine formula."""
        lat1, lon1 = math.radians(wp1.coordinates.latitude), math.radians(wp1.coordinates.longitude)
        lat2, lon2 = math.radians(wp2.coordinates.latitude), math.radians(wp2.coordinates.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in meters
        r = 6371000
        
        # Calculate horizontal distance
        horizontal_distance = r * c
        
        # Add vertical distance if altitudes are available
        alt1 = wp1.coordinates.altitude or 0
        alt2 = wp2.coordinates.altitude or 0
        vertical_distance = abs(alt2 - alt1)
        
        # Calculate 3D distance
        return math.sqrt(horizontal_distance**2 + vertical_distance**2)
    
    def _get_bounding_box_dict(self, bbox) -> Optional[Dict[str, float]]:
        """Convert bounding box to dictionary."""
        if bbox is None:
            return None
        
        return {
            "min_latitude": bbox.min_latitude,
            "max_latitude": bbox.max_latitude,
            "min_longitude": bbox.min_longitude,
            "max_longitude": bbox.max_longitude
        }
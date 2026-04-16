"""
Waypoint and flight path models.
"""

from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, validator

from .coordinates import Coordinates, HeightMode


class WaypointTurnMode(str, Enum):
    """Waypoint turn modes."""
    COORDINATE_TURN = "coordinateTurn"
    TO_POINT_STOP_DISCONTINUITY = "toPointAndStopWithDiscontinuityCurvature"
    TO_POINT_STOP_CONTINUITY = "toPointAndStopWithContinuityCurvature"
    TO_POINT_PASS_CONTINUITY = "toPointAndPassWithContinuityCurvature"


class HeadingMode(str, Enum):
    """Aircraft heading modes."""
    FOLLOW_WAYLINE = "followWayline"
    MANUALLY = "manually"
    FIXED = "fixed"
    SMOOTH_TRANSITION = "smoothTransition"
    TOWARD_POI = "towardPOI"


class ActionTriggerType(str, Enum):
    """Action trigger types."""
    REACH_POINT = "reachPoint"
    BETWEEN_ADJACENT_POINTS = "betweenAdjacentPoints"
    MULTIPLE_TIMING = "multipleTiming"
    MULTIPLE_DISTANCE = "multipleDistance"


class ActionType(str, Enum):
    """Available action types."""
    TAKE_PHOTO = "takePhoto"
    START_RECORD = "startRecord"
    STOP_RECORD = "stopRecord"
    FOCUS = "focus"
    ZOOM = "zoom"
    CUSTOM_DIR_NAME = "customDirName"
    GIMBAL_ROTATE = "gimbalRotate"
    ROTATE_YAW = "rotateYaw"
    HOVER = "hover"
    GIMBAL_EVENLY_ROTATE = "gimbalEvenlyRotate"
    ORIENTED_SHOOT = "orientedShoot"
    PANO_SHOT = "panoShot"


class ActionTrigger(BaseModel):
    """Action trigger configuration."""
    
    trigger_type: ActionTriggerType = Field(..., description="Type of trigger")
    trigger_param: Optional[float] = Field(None, description="Trigger parameter (time in seconds or distance in meters)")


class Action(BaseModel):
    """Waypoint action definition."""
    
    action_id: int = Field(..., ge=0, description="Unique action ID within the group")
    action_type: ActionType = Field(..., description="Type of action to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters")


class ActionGroup(BaseModel):
    """Group of actions to execute at waypoints."""
    
    group_id: int = Field(..., ge=0, description="Unique group ID")
    start_index: int = Field(..., ge=0, description="Starting waypoint index")
    end_index: int = Field(..., ge=0, description="Ending waypoint index")
    trigger: ActionTrigger = Field(..., description="Trigger configuration")
    actions: List[Action] = Field(default_factory=list, description="List of actions in the group")
    
    @validator('end_index')
    def validate_index_order(cls, v, values):
        """Ensure end_index >= start_index."""
        if 'start_index' in values and v < values['start_index']:
            raise ValueError("end_index must be >= start_index")
        return v


class HeadingParam(BaseModel):
    """Aircraft heading parameters."""
    
    heading_mode: HeadingMode = Field(..., description="Heading control mode")
    heading_angle: Optional[float] = Field(None, ge=-180, le=180, description="Target heading angle in degrees")
    poi_point: Optional[Coordinates] = Field(None, description="Point of interest coordinates")
    path_mode: Optional[str] = Field(None, description="Path mode for heading changes")


class TurnParam(BaseModel):
    """Waypoint turn parameters."""
    
    turn_mode: WaypointTurnMode = Field(..., description="Turn mode at waypoint")
    damping_distance: Optional[float] = Field(None, ge=0, description="Turn damping distance in meters")


class Waypoint(BaseModel):
    """Individual waypoint definition."""
    
    index: int = Field(..., ge=0, description="Waypoint index (0-based)")
    coordinates: Coordinates = Field(..., description="Waypoint coordinates")
    
    # Height settings
    height: Optional[float] = Field(None, description="Waypoint height")
    ellipsoid_height: Optional[float] = Field(None, description="Ellipsoid height (WGS84)")
    use_global_height: bool = Field(True, description="Use global height setting")
    
    # Speed settings
    speed: Optional[float] = Field(None, ge=1, le=15, description="Flight speed to this waypoint (m/s)")
    use_global_speed: bool = Field(True, description="Use global speed setting")
    
    # Heading settings
    heading_param: Optional[HeadingParam] = Field(None, description="Heading parameters")
    use_global_heading: bool = Field(True, description="Use global heading settings")
    
    # Turn settings
    turn_param: Optional[TurnParam] = Field(None, description="Turn parameters")
    use_global_turn: bool = Field(True, description="Use global turn settings")
    
    # Gimbal settings
    gimbal_pitch_angle: Optional[float] = Field(None, ge=-120, le=45, description="Gimbal pitch angle in degrees")
    
    # Actions
    action_groups: List[ActionGroup] = Field(default_factory=list, description="Action groups for this waypoint")
    
    # Safety
    is_risky: bool = Field(False, description="Mark as risky waypoint")
    
    @validator('index')
    def validate_index(cls, v):
        """Validate waypoint index."""
        if v < 0:
            raise ValueError("Waypoint index must be non-negative")
        return v


class FlightPath(BaseModel):
    """Complete flight path with waypoints."""
    
    waypoints: List[Waypoint] = Field(..., description="List of waypoints")
    
    # Global settings
    global_speed: float = Field(5.0, ge=1, le=15, description="Global flight speed (m/s)")
    global_height: Optional[float] = Field(None, description="Global flight height")
    height_mode: HeightMode = Field(HeightMode.EGM96, description="Height reference mode")
    
    # Global heading settings
    global_heading_param: Optional[HeadingParam] = Field(None, description="Global heading parameters")
    
    # Global turn settings
    global_turn_mode: WaypointTurnMode = Field(
        WaypointTurnMode.TO_POINT_STOP_DISCONTINUITY, 
        description="Global turn mode"
    )
    use_straight_line: bool = Field(False, description="Use straight line segments")
    
    @validator('waypoints')
    def validate_waypoints(cls, v):
        """Validate waypoint list."""
        if len(v) < 2:
            raise ValueError("Flight path must have at least 2 waypoints")
        
        # Check for sequential indices
        for i, waypoint in enumerate(v):
            if waypoint.index != i:
                raise ValueError(f"Waypoint index mismatch: expected {i}, got {waypoint.index}")
        
        return v
    
    def get_bounding_box(self):
        """Get bounding box of all waypoints."""
        if not self.waypoints:
            return None
        
        lats = [wp.coordinates.latitude for wp in self.waypoints]
        lons = [wp.coordinates.longitude for wp in self.waypoints]
        
        from .coordinates import BoundingBox
        return BoundingBox(
            min_latitude=min(lats),
            max_latitude=max(lats),
            min_longitude=min(lons),
            max_longitude=max(lons)
        )
    
    def total_distance(self) -> float:
        """Calculate total flight path distance in meters."""
        # TODO: Implement actual distance calculation
        return len(self.waypoints) * 100.0  # Placeholder
    
    def estimated_flight_time(self) -> float:
        """Estimate total flight time in seconds."""
        distance = self.total_distance()
        return distance / self.global_speed
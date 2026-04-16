"""
Aircraft and payload configuration models.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

from pydantic import BaseModel, Field


class AircraftModel(str, Enum):
    """Supported aircraft models."""
    M300_RTK = "M300_RTK"
    M350_RTK = "M350_RTK"
    M30 = "M30"
    M30T = "M30T"
    M3E = "M3E"
    M3T = "M3T"
    M3M = "M3M"
    M3D = "M3D"
    M3TD = "M3TD"


class PayloadModel(str, Enum):
    """Supported payload models."""
    H20 = "H20"
    H20T = "H20T"
    H20N = "H20N"
    H30 = "H30"
    H30T = "H30T"
    M30_DUAL_CAMERA = "M30_DUAL_CAMERA"
    M30T_TRIPLE_CAMERA = "M30T_TRIPLE_CAMERA"
    M3E_CAMERA = "M3E_CAMERA"
    M3T_CAMERA = "M3T_CAMERA"
    M3M_CAMERA = "M3M_CAMERA"
    M3D_CAMERA = "M3D_CAMERA"
    M3TD_CAMERA = "M3TD_CAMERA"
    PSDK_PAYLOAD = "PSDK_PAYLOAD"


class PayloadPosition(int, Enum):
    """Payload mounting positions."""
    POSITION_0 = 0  # Main gimbal / Left front (M300/M350)
    POSITION_1 = 1  # Right front (M300/M350)
    POSITION_2 = 2  # Top (M300/M350)


class FlyToWaylineMode(str, Enum):
    """Flight modes to first waypoint."""
    SAFELY = "safely"
    POINT_TO_POINT = "pointToPoint"


class FinishAction(str, Enum):
    """Actions after mission completion."""
    GO_HOME = "goHome"
    NO_ACTION = "noAction"
    AUTO_LAND = "autoLand"
    GOTO_FIRST_WAYPOINT = "gotoFirstWaypoint"


class RCLostAction(str, Enum):
    """Actions when RC signal is lost."""
    GO_BACK = "goBack"
    LANDING = "landing"
    HOVER = "hover"


class AircraftSpecs(BaseModel):
    """Aircraft specifications and capabilities."""
    
    model: AircraftModel = Field(..., description="Aircraft model")
    enum_value: int = Field(..., description="DJI enum value for aircraft")
    sub_enum_value: int = Field(0, description="DJI sub-enum value")
    
    # Flight capabilities
    max_flight_speed: float = Field(..., description="Maximum flight speed (m/s)")
    max_flight_height: float = Field(..., description="Maximum flight height (m)")
    max_flight_distance: float = Field(..., description="Maximum flight distance (m)")
    battery_life: float = Field(..., description="Battery life (minutes)")
    
    # Payload capabilities
    supported_payloads: List[PayloadModel] = Field(default_factory=list, description="Supported payload models")
    payload_positions: List[PayloadPosition] = Field(default_factory=list, description="Available payload positions")
    
    # Feature support
    supports_obstacle_avoidance: bool = Field(False, description="Supports obstacle avoidance")
    supports_terrain_following: bool = Field(False, description="Supports terrain following")
    supports_rtk: bool = Field(False, description="Supports RTK positioning")


class PayloadSpecs(BaseModel):
    """Payload specifications and capabilities."""
    
    model: PayloadModel = Field(..., description="Payload model")
    enum_value: int = Field(..., description="DJI enum value for payload")
    
    # Camera capabilities
    has_zoom: bool = Field(False, description="Has zoom capability")
    has_thermal: bool = Field(False, description="Has thermal imaging")
    has_lidar: bool = Field(False, description="Has LiDAR")
    
    # Gimbal capabilities
    gimbal_pitch_range: Tuple[float, float] = Field((-90, 30), description="Gimbal pitch range (min, max)")
    gimbal_yaw_range: Tuple[float, float] = Field((-180, 180), description="Gimbal yaw range (min, max)")
    gimbal_roll_range: Tuple[float, float] = Field((-45, 45), description="Gimbal roll range (min, max)")
    
    # Image formats
    supported_image_formats: List[str] = Field(default_factory=list, description="Supported image formats")
    
    # Focus capabilities
    supports_auto_focus: bool = Field(True, description="Supports auto focus")
    supports_manual_focus: bool = Field(True, description="Supports manual focus")


class MissionConfig(BaseModel):
    """Mission configuration parameters."""
    
    # Aircraft and payload
    aircraft: AircraftSpecs = Field(..., description="Aircraft specifications")
    payload: PayloadSpecs = Field(..., description="Payload specifications")
    payload_position: PayloadPosition = Field(PayloadPosition.POSITION_0, description="Payload mounting position")
    
    # Flight behavior
    fly_to_wayline_mode: FlyToWaylineMode = Field(FlyToWaylineMode.SAFELY, description="Flight mode to first waypoint")
    finish_action: FinishAction = Field(FinishAction.GO_HOME, description="Action after mission completion")
    
    # RC lost behavior
    exit_on_rc_lost: bool = Field(False, description="Continue mission when RC signal is lost")
    rc_lost_action: RCLostAction = Field(RCLostAction.HOVER, description="Action when RC signal is lost")
    
    # Safety settings
    takeoff_security_height: float = Field(20.0, ge=1.2, le=1500, description="Safe takeoff height (m)")
    global_transitional_speed: float = Field(8.0, ge=1, le=15, description="Speed between waylines (m/s)")
    global_rth_height: float = Field(100.0, description="Return to home height (m)")
    
    # Reference point
    takeoff_ref_point: Optional[Tuple[float, float, float]] = Field(None, description="Reference takeoff point (lat, lon, alt)")
    takeoff_ref_point_agl_height: Optional[float] = Field(None, description="Reference point AGL height")


class FlightPlan(BaseModel):
    """Complete flight plan with mission configuration."""
    
    mission_config: MissionConfig = Field(..., description="Mission configuration")
    templates: List[Dict[str, Any]] = Field(default_factory=list, description="Flight templates")
    
    # Metadata
    author: Optional[str] = Field(None, description="Flight plan author")
    create_time: Optional[int] = Field(None, description="Creation timestamp (Unix)")
    update_time: Optional[int] = Field(None, description="Last update timestamp (Unix)")
    
    def get_aircraft_model(self) -> AircraftModel:
        """Get the aircraft model."""
        return self.mission_config.aircraft.model
    
    def get_payload_model(self) -> PayloadModel:
        """Get the payload model."""
        return self.mission_config.payload.model
    
    def is_compatible(self, aircraft: AircraftModel, payload: PayloadModel) -> bool:
        """Check if the flight plan is compatible with given aircraft and payload."""
        return (
            self.mission_config.aircraft.model == aircraft and
            payload in self.mission_config.aircraft.supported_payloads
        )
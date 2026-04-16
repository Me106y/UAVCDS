"""
Data models for DJI Waypoint MCP Service.
"""

from .coordinates import (
    Coordinates,
    CoordinateSystem,
    HeightMode,
    CoordinateTransform,
    BoundingBox,
)
from .waypoint import (
    Waypoint,
    FlightPath,
    Action,
    ActionGroup,
    ActionTrigger,
    ActionType,
    ActionTriggerType,
    HeadingMode,
    WaypointTurnMode,
)
from .aircraft import (
    AircraftModel,
    PayloadModel,
    AircraftSpecs,
    PayloadSpecs,
    MissionConfig,
    FlightPlan,
    FlyToWaylineMode,
    FinishAction,
    RCLostAction,
)

__all__ = [
    # Coordinates
    "Coordinates",
    "CoordinateSystem", 
    "HeightMode",
    "CoordinateTransform",
    "BoundingBox",
    # Waypoints
    "Waypoint",
    "FlightPath",
    "Action",
    "ActionGroup",
    "ActionTrigger",
    "ActionType",
    "ActionTriggerType",
    "HeadingMode",
    "WaypointTurnMode",
    # Aircraft
    "AircraftModel",
    "PayloadModel",
    "AircraftSpecs",
    "PayloadSpecs",
    "MissionConfig",
    "FlightPlan",
    "FlyToWaylineMode",
    "FinishAction",
    "RCLostAction",
]
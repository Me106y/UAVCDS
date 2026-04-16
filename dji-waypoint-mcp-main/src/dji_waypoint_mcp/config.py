"""
Configuration management for DJI Waypoint MCP Service.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # MCP server configuration
    server_name: str = Field(default="dji-waypoint-mcp", env="MCP_SERVER_NAME")
    server_version: str = Field(default="0.1.0", env="MCP_SERVER_VERSION")
    
    # File paths
    temp_dir: Path = Field(default=Path("/tmp/dji-waypoint-mcp"), env="TEMP_DIR")
    output_dir: Path = Field(default=Path("./output"), env="OUTPUT_DIR")
    
    # Coordinate system settings
    default_coordinate_system: str = Field(default="WGS84", env="DEFAULT_COORD_SYS")
    default_height_mode: str = Field(default="EGM96", env="DEFAULT_HEIGHT_MODE")
    
    # Safety limits
    max_waypoints: int = Field(default=1000, env="MAX_WAYPOINTS")
    max_flight_distance: float = Field(default=50000.0, env="MAX_FLIGHT_DISTANCE")  # meters
    max_flight_height: float = Field(default=500.0, env="MAX_FLIGHT_HEIGHT")  # meters
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def setup_logging(settings: Optional[Settings] = None) -> None:
    """Setup logging configuration."""
    if settings is None:
        settings = Settings()
    
    # Create log directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 确保 StreamHandler 输出到 stderr
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format,
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler(log_dir / "dji-waypoint-mcp.log", encoding='utf-8'),
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("mcp").setLevel(logging.INFO)
    logging.getLogger("dji_waypoint_mcp").setLevel(
        getattr(logging, settings.log_level.upper())
    )


# Global settings instance
settings = Settings()
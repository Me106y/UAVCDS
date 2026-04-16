"""
倾斜摄影任务规划工具。
"""

import math
from typing import Any, Dict, List, Tuple, Optional, Union
from enum import Enum
from dataclasses import dataclass

import numpy as np
from shapely.geometry import Polygon, Point, LineString
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
)
from ..utils.geometry import geometry_calculator
from ..config import settings


class ObliqueDirection(str, Enum):
    """倾斜摄影方向。"""
    NADIR = "nadir"
    FORWARD = "forward"
    BACKWARD = "backward"
    LEFT = "left"
    RIGHT = "right"


class ObliqueAngle(BaseModel):
    """倾斜摄影角度配置。"""
    direction: ObliqueDirection
    gimbal_pitch: float = Field(..., ge=-90, le=0)
    gimbal_yaw: Optional[float] = Field(None, ge=-180, le=180)
    enabled: bool = Field(default=True)


class SurveyAreaPoint(BaseModel):
    """测区点坐标。"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class ObliqueMissionInput(BaseModel):
    """倾斜摄影任务输入参数。"""
    survey_area: List[SurveyAreaPoint] = Field(..., min_items=3, description="测区多边形顶点")
    flight_height: float = Field(default=100.0, ge=10, le=1500, description="飞行高度(米)")
    overlap_rate: float = Field(default=80.0, ge=50, le=95, description="重叠率(%)")
    sidelap_rate: float = Field(default=70.0, ge=30, le=90, description="旁向重叠率(%)")
    flight_direction: float = Field(default=0.0, ge=0, le=360, description="飞行方向(度)")
    flight_speed: float = Field(default=5.0, ge=1, le=15, description="飞行速度(m/s)")
    aircraft_type: str = Field(default="M30", description="无人机型号")
    margin: float = Field(default=20.0, ge=0, le=100, description="测区边界余量(米)")
    shoot_mode: str = Field(default="time", description="拍摄模式")
    
    # 倾斜摄影特定参数
    oblique_angles: List[ObliqueAngle] = Field(default=None, description="倾斜摄影角度")
    use_separate_flights: bool = Field(default=True, description="使用独立航线")
    optimize_flight_order: bool = Field(default=True, description="优化飞行顺序")
    
    @validator('oblique_angles', pre=True, always=True)
    def set_default_oblique_angles(cls, v):
        """设置默认倾斜角度。"""
        if v is None:
            return [
                ObliqueAngle(direction=ObliqueDirection.NADIR, gimbal_pitch=-90),
                ObliqueAngle(direction=ObliqueDirection.FORWARD, gimbal_pitch=-45),
                ObliqueAngle(direction=ObliqueDirection.BACKWARD, gimbal_pitch=-45, gimbal_yaw=180),
                ObliqueAngle(direction=ObliqueDirection.LEFT, gimbal_pitch=-45, gimbal_yaw=-90),
                ObliqueAngle(direction=ObliqueDirection.RIGHT, gimbal_pitch=-45, gimbal_yaw=90)
            ]
        return v


class ObliqueMissionTool(BaseTool, ValidationMixin):
    """倾斜摄影任务工具。"""
    
    def __init__(self):
        """初始化倾斜摄影工具。"""
        super().__init__()
        self.geometry_calc = geometry_calculator
    
    def get_tool_definition(self) -> Tool:
        """获取MCP工具定义。"""
        return Tool(
            name="plan_oblique_mission",
            description="规划倾斜摄影任务，支持五方向航线生成",
            inputSchema={
                "type": "object",
                "properties": {
                    "survey_area": {
                        "type": "array",
                        "description": "测区多边形顶点坐标",
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
                        "minimum": 10,
                        "maximum": 1500,
                        "default": 100.0,
                        "description": "飞行高度(米)"
                    },
                    "overlap_rate": {
                        "type": "number",
                        "minimum": 50,
                        "maximum": 95,
                        "default": 80.0,
                        "description": "重叠率(%)"
                    },
                    "sidelap_rate": {
                        "type": "number",
                        "minimum": 30,
                        "maximum": 90,
                        "default": 70.0,
                        "description": "旁向重叠率(%)"
                    },
                    "flight_direction": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 360,
                        "default": 0.0,
                        "description": "飞行方向(度)"
                    },
                    "flight_speed": {
                        "type": "number",
                        "minimum": 1,
                        "maximum": 15,
                        "default": 5.0,
                        "description": "飞行速度(m/s)"
                    },
                    "aircraft_type": {
                        "type": "string",
                        "enum": ["M300_RTK", "M350_RTK", "M30", "M30T", "M3E", "M3T", "M3M", "M3D", "M3TD"],
                        "default": "M30",
                        "description": "无人机型号"
                    },
                    "oblique_angles": {
                        "type": "array",
                        "description": "倾斜摄影角度配置",
                        "items": {
                            "type": "object",
                            "properties": {
                                "direction": {
                                    "type": "string",
                                    "enum": ["nadir", "forward", "backward", "left", "right"]
                                },
                                "gimbal_pitch": {
                                    "type": "number",
                                    "minimum": -90,
                                    "maximum": 0
                                },
                                "gimbal_yaw": {
                                    "type": "number",
                                    "minimum": -180,
                                    "maximum": 180
                                },
                                "enabled": {
                                    "type": "boolean",
                                    "default": True
                                }
                            },
                            "required": ["direction", "gimbal_pitch"]
                        }
                    },
                    "use_separate_flights": {
                        "type": "boolean",
                        "default": True,
                        "description": "使用独立航线"
                    }
                },
                "required": ["survey_area"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行倾斜摄影任务规划。"""
        try:
            # 验证输入参数
            mission_input = ObliqueMissionInput(**arguments)
            
            self.logger.info(f"规划倾斜摄影任务，测区点数: {len(mission_input.survey_area)}")
            
            # 创建测区多边形
            survey_polygon = self._create_survey_polygon(mission_input.survey_area)
            
            # 获取启用的角度
            enabled_angles = [angle for angle in mission_input.oblique_angles if angle.enabled]
            
            if not enabled_angles:
                raise ValueError("至少需要启用一个倾斜角度")
            
            # 为每个角度生成航线
            flight_results = []
            total_waypoints = 0
            total_photos = 0
            total_distance = 0.0
            total_time = 0.0
            
            for angle in enabled_angles:
                angle_result = self._generate_flight_for_angle(
                    survey_polygon,
                    mission_input,
                    angle
                )
                flight_results.append(angle_result)
                total_waypoints += angle_result["waypoint_count"]
                total_photos += angle_result["estimated_photos"]
                total_distance += angle_result["total_distance"]
                total_time += angle_result["estimated_flight_time"]
            
            # 准备响应数据
            response_data = {
                "flight_paths": flight_results,
                "survey_configuration": {
                    "area_hectares": self._calculate_area_hectares(survey_polygon),
                    "flight_height": mission_input.flight_height,
                    "overlap_rate": mission_input.overlap_rate,
                    "sidelap_rate": mission_input.sidelap_rate,
                    "flight_direction": mission_input.flight_direction,
                    "use_separate_flights": mission_input.use_separate_flights
                },
                "overall_statistics": {
                    "total_waypoints": total_waypoints,
                    "total_photos": total_photos,
                    "total_distance": round(total_distance, 2),
                    "total_flight_time": round(total_time, 1),
                    "enabled_angles": len(enabled_angles)
                }
            }
            
            return self.format_success_response(
                f"倾斜摄影任务规划完成，生成 {len(enabled_angles)} 个角度的航线",
                response_data
            )
            
        except ValidationError as e:
            self.logger.error(f"倾斜摄影任务验证错误: {e}")
            return self.format_error_response(f"输入参数无效: {e}")
        
        except Exception as e:
            self.logger.error(f"倾斜摄影任务规划失败: {e}", exc_info=True)
            return self.format_error_response(f"任务规划失败: {e}")
    
    def _create_survey_polygon(self, survey_area: List[SurveyAreaPoint]) -> Polygon:
        """创建测区多边形。"""
        coordinates = [(point.longitude, point.latitude) for point in survey_area]
        
        # 确保多边形闭合
        if coordinates[0] != coordinates[-1]:
            coordinates.append(coordinates[0])
        
        return Polygon(coordinates)
    
    def _generate_flight_for_angle(
        self,
        survey_polygon: Polygon,
        mission_input: ObliqueMissionInput,
        angle: ObliqueAngle
    ) -> Dict[str, Any]:
        """为特定角度生成航线。"""
        # 简化的航线生成逻辑
        # 实际实现中应该根据角度调整飞行方向和云台设置
        
        # 计算航线数量（简化）
        flight_lines = 5  # 假设5条航线
        waypoints_per_line = 10  # 每条航线10个航点
        waypoint_count = flight_lines * waypoints_per_line
        
        # 估算距离和时间
        area_hectares = self._calculate_area_hectares(survey_polygon)
        total_distance = area_hectares * 100  # 简化计算
        estimated_flight_time = total_distance / mission_input.flight_speed / 60  # 转换为分钟
        
        # 估算照片数量
        photo_interval = 2.0  # 假设2秒间隔
        estimated_photos = int(estimated_flight_time * 60 / photo_interval)
        
        return {
            "direction": angle.direction,
            "gimbal_pitch": angle.gimbal_pitch,
            "gimbal_yaw": angle.gimbal_yaw,
            "waypoint_count": waypoint_count,
            "flight_lines": flight_lines,
            "estimated_photos": estimated_photos,
            "total_distance": round(total_distance, 2),
            "estimated_flight_time": round(estimated_flight_time, 1)
        }
    
    def _calculate_area_hectares(self, polygon: Polygon) -> float:
        """计算多边形面积（公顷）。"""
        # 简化的面积计算
        area_sq_degrees = polygon.area
        area_sq_meters = area_sq_degrees * (111000 ** 2)  # 粗略转换
        area_hectares = area_sq_meters / 10000
        return round(area_hectares, 2)
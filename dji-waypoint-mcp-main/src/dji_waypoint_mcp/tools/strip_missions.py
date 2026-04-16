"""
航带飞行任务规划工具。
用于线性路径、走廊巡检、管道巡查等航带飞行任务。
"""

import math
import random
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass

import numpy as np
from shapely.geometry import LineString, Point, Polygon
# parallel_offset is now a method of geometry objects in newer Shapely versions
from mcp.types import Tool
from pydantic import BaseModel, Field, ValidationError, field_validator

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
    WaypointTurnMode
)
from ..utils.geometry import geometry_calculator
from ..config import settings


class StripType(str, Enum):
    """航带类型。"""
    LINEAR = "linear"           # 线性航带
    CORRIDOR = "corridor"       # 走廊巡检
    PIPELINE = "pipeline"       # 管道巡查
    POWERLINE = "powerline"     # 电力线巡检
    ROAD = "road"              # 道路巡查
    RIVER = "river"            # 河流巡查


class FlightPattern(str, Enum):
    """飞行模式。"""
    SINGLE_LINE = "single_line"     # 单线飞行
    PARALLEL_LINES = "parallel_lines"  # 平行线飞行
    ZIGZAG = "zigzag"              # 之字形飞行
    BACK_AND_FORTH = "back_and_forth"  # 往返飞行


class StripMissionInput(BaseModel):
    """航带任务输入参数。"""
    strip_type: StripType = Field(..., description="航带类型")
    flight_pattern: FlightPattern = Field(default=FlightPattern.SINGLE_LINE, description="飞行模式")
    
    # 路径定义
    path_points: List[Dict[str, float]] = Field(..., min_items=2, description="路径关键点")
    strip_width: float = Field(default=100.0, ge=10, le=1000, description="航带宽度(米)")
    
    # 飞行参数
    flight_height: float = Field(default=100.0, ge=10, le=500, description="飞行高度(米)")
    flight_speed: float = Field(default=5.0, ge=1, le=15, description="飞行速度(m/s)")
    overlap_rate: float = Field(default=80.0, ge=50, le=95, description="重叠率(%)")
    sidelap_rate: float = Field(default=70.0, ge=30, le=90, description="旁向重叠率(%)")
    
    # 相机参数
    gimbal_pitch: float = Field(default=-90.0, ge=-90, le=0, description="云台俯仰角(度)")
    gimbal_yaw: float = Field(default=0.0, ge=-180, le=180, description="云台偏航角(度)")
    
    # 任务参数
    aircraft_type: str = Field(default="M30", description="无人机型号")
    shoot_mode: str = Field(default="time", description="拍摄模式")
    margin: float = Field(default=10.0, ge=0, le=50, description="航带边界余量(米)")
    
    # 高级选项
    follow_terrain: bool = Field(default=False, description="是否跟随地形")
    adaptive_height: bool = Field(default=False, description="是否自适应高度")
    safety_buffer: float = Field(default=20.0, ge=5, le=100, description="安全缓冲距离(米)")
    
    @field_validator('path_points')
    @classmethod
    def validate_path_points(cls, v):
        """验证路径点。"""
        if len(v) < 2:
            raise ValueError("至少需要2个路径点")
        
        for point in v:
            if 'latitude' not in point or 'longitude' not in point:
                raise ValueError("路径点必须包含latitude和longitude")
            
            lat, lon = point['latitude'], point['longitude']
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise ValueError("路径点坐标超出有效范围")
        
        return v


class StripMissionTool(BaseTool, ValidationMixin):
    """航带飞行任务工具。"""
    
    def __init__(self):
        """初始化航带任务工具。"""
        super().__init__()
        self.geometry_calc = geometry_calculator
    
    def get_tool_definition(self) -> Tool:
        """获取MCP工具定义。"""
        return Tool(
            name="plan_strip_mission",
            description="规划线性航带飞行任务，适用于走廊巡检、管道巡查等场景",
            inputSchema={
                "type": "object",
                "properties": {
                    "strip_type": {
                        "type": "string",
                        "enum": ["linear", "corridor", "pipeline", "powerline", "road", "river"],
                        "description": "航带类型"
                    },
                    "flight_pattern": {
                        "type": "string",
                        "enum": ["single_line", "parallel_lines", "zigzag", "back_and_forth"],
                        "default": "single_line",
                        "description": "飞行模式"
                    },
                    "path_points": {
                        "type": "array",
                        "description": "路径关键点坐标",
                        "minItems": 2,
                        "items": {
                            "type": "object",
                            "properties": {
                                "latitude": {"type": "number", "minimum": -90, "maximum": 90},
                                "longitude": {"type": "number", "minimum": -180, "maximum": 180},
                                "altitude": {"type": "number", "minimum": 0, "maximum": 1000}
                            },
                            "required": ["latitude", "longitude"]
                        }
                    },
                    "strip_width": {
                        "type": "number",
                        "minimum": 10,
                        "maximum": 1000,
                        "default": 100.0,
                        "description": "航带宽度(米)"
                    },
                    "flight_height": {
                        "type": "number",
                        "minimum": 10,
                        "maximum": 500,
                        "default": 100.0,
                        "description": "飞行高度(米)"
                    },
                    "flight_speed": {
                        "type": "number",
                        "minimum": 1,
                        "maximum": 15,
                        "default": 5.0,
                        "description": "飞行速度(m/s)"
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
                    "gimbal_pitch": {
                        "type": "number",
                        "minimum": -90,
                        "maximum": 0,
                        "default": -90.0,
                        "description": "云台俯仰角(度)"
                    },
                    "gimbal_yaw": {
                        "type": "number",
                        "minimum": -180,
                        "maximum": 180,
                        "default": 0.0,
                        "description": "云台偏航角(度)"
                    },
                    "aircraft_type": {
                        "type": "string",
                        "enum": ["M300_RTK", "M350_RTK", "M30", "M30T", "M3E", "M3T", "M3M", "M3D", "M3TD"],
                        "default": "M30",
                        "description": "无人机型号"
                    },
                    "shoot_mode": {
                        "type": "string",
                        "enum": ["time", "distance"],
                        "default": "time",
                        "description": "拍摄模式"
                    },
                    "margin": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 50,
                        "default": 10.0,
                        "description": "航带边界余量(米)"
                    },
                    "follow_terrain": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否跟随地形"
                    },
                    "adaptive_height": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否自适应高度"
                    },
                    "safety_buffer": {
                        "type": "number",
                        "minimum": 5,
                        "maximum": 100,
                        "default": 20.0,
                        "description": "安全缓冲距离(米)"
                    }
                },
                "required": ["strip_type", "path_points"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行航带任务规划。"""
        try:
            # 验证输入参数
            mission_input = StripMissionInput(**arguments)
            
            self.logger.info(f"规划航带任务: {mission_input.strip_type} - {mission_input.flight_pattern}")
            
            # 创建路径线
            path_line = self._create_path_line(mission_input.path_points)
            
            # 生成航带边界
            strip_boundary = self._generate_strip_boundary(
                path_line, 
                mission_input.strip_width, 
                mission_input.margin
            )
            
            # 根据飞行模式生成航线
            if mission_input.flight_pattern == FlightPattern.SINGLE_LINE:
                flight_lines = self._generate_single_line_flight(path_line, mission_input)
            elif mission_input.flight_pattern == FlightPattern.PARALLEL_LINES:
                flight_lines = self._generate_parallel_lines_flight(path_line, mission_input)
            elif mission_input.flight_pattern == FlightPattern.ZIGZAG:
                flight_lines = self._generate_zigzag_flight(path_line, mission_input)
            elif mission_input.flight_pattern == FlightPattern.BACK_AND_FORTH:
                flight_lines = self._generate_back_and_forth_flight(path_line, mission_input)
            else:
                raise ValueError(f"不支持的飞行模式: {mission_input.flight_pattern}")
            
            # 转换为航点
            waypoints = self._flight_lines_to_waypoints(
                flight_lines, 
                mission_input
            )
            
            # 添加拍摄动作
            waypoints = self._add_photo_actions(waypoints, mission_input)
            
            # 创建飞行路径
            flight_path = FlightPath(
                waypoints=waypoints,
                global_speed=mission_input.flight_speed,
                global_height=mission_input.flight_height,
                height_mode=HeightMode.EGM96,
                global_turn_mode=WaypointTurnMode.TO_POINT_STOP_DISCONTINUITY
            )
            
            # 计算任务统计
            statistics = self._calculate_mission_statistics(
                flight_path, 
                strip_boundary, 
                mission_input
            )
            
            # 准备响应数据
            response_data = {
                "flight_path": {
                    "waypoint_count": len(waypoints),
                    "flight_lines": len(flight_lines),
                    "total_distance": statistics["total_distance"],
                    "estimated_flight_time": statistics["estimated_flight_time"]
                },
                "strip_configuration": {
                    "strip_type": mission_input.strip_type,
                    "flight_pattern": mission_input.flight_pattern,
                    "strip_width": mission_input.strip_width,
                    "strip_length": statistics["strip_length"],
                    "coverage_area": statistics["coverage_area"],
                    "path_points_count": len(mission_input.path_points)
                },
                "mission_parameters": {
                    "flight_height": mission_input.flight_height,
                    "flight_speed": mission_input.flight_speed,
                    "overlap_rate": mission_input.overlap_rate,
                    "sidelap_rate": mission_input.sidelap_rate,
                    "gimbal_pitch": mission_input.gimbal_pitch,
                    "gimbal_yaw": mission_input.gimbal_yaw
                },
                "photo_configuration": {
                    "shoot_mode": mission_input.shoot_mode,
                    "photo_interval": statistics["photo_interval"],
                    "estimated_photos": statistics["estimated_photos"]
                },
                "statistics": statistics
            }
            
            return self.format_success_response(
                f"航带任务规划完成，生成 {len(waypoints)} 个航点",
                response_data
            )
            
        except ValidationError as e:
            self.logger.error(f"航带任务验证错误: {e}")
            return self.format_error_response(f"输入参数无效: {e}")
        
        except ValueError as e:
            self.logger.error(f"航带任务值错误: {e}")
            return self.format_error_response(str(e))
        
        except Exception as e:
            self.logger.error(f"航带任务意外错误: {e}", exc_info=True)
            return self.format_error_response(f"航带任务规划失败: {e}")
    
    def _create_path_line(self, path_points: List[Dict[str, float]]) -> LineString:
        """创建路径线。"""
        coordinates = []
        for point in path_points:
            coordinates.append((point['longitude'], point['latitude']))
        
        return LineString(coordinates)
    
    def _generate_strip_boundary(
        self, 
        path_line: LineString, 
        strip_width: float, 
        margin: float
    ) -> Polygon:
        """生成航带边界。"""
        # 将宽度从米转换为度（粗略转换）
        width_degrees = (strip_width + margin * 2) / 111000
        
        # 创建缓冲区
        buffer_polygon = path_line.buffer(width_degrees / 2)
        
        return buffer_polygon
    
    def _generate_single_line_flight(
        self, 
        path_line: LineString, 
        mission_input: StripMissionInput
    ) -> List[LineString]:
        """生成单线飞行航线。"""
        return [path_line]
    
    def _generate_parallel_lines_flight(
        self, 
        path_line: LineString, 
        mission_input: StripMissionInput
    ) -> List[LineString]:
        """生成平行线飞行航线。"""
        flight_lines = []
        
        # 计算相机覆盖宽度
        camera_specs = self._get_camera_specs(mission_input.aircraft_type)
        ground_width = self._calculate_ground_coverage_width(
            mission_input.flight_height,
            camera_specs,
            mission_input.gimbal_pitch
        )
        
        # 计算航线间距
        sidelap_factor = (100 - mission_input.sidelap_rate) / 100
        line_spacing_meters = ground_width * sidelap_factor
        line_spacing_degrees = line_spacing_meters / 111000
        
        # 计算需要的航线数量
        strip_width_degrees = mission_input.strip_width / 111000
        num_lines = max(1, int(strip_width_degrees / line_spacing_degrees) + 1)
        
        # 生成平行航线
        center_offset = (num_lines - 1) * line_spacing_degrees / 2
        
        for i in range(num_lines):
            offset_distance = i * line_spacing_degrees - center_offset
            
            try:
                if offset_distance == 0:
                    parallel_line = path_line
                else:
                    # Use the parallel_offset method of the geometry object
                    try:
                        parallel_line = path_line.parallel_offset(offset_distance, side='left')
                    except AttributeError:
                        # Fallback for older Shapely versions
                        try:
                            from shapely.ops import parallel_offset as parallel_offset_func
                            parallel_line = parallel_offset_func(path_line, offset_distance, side='left')
                        except ImportError:
                            self.logger.error("无法导入parallel_offset函数，跳过此平行线")
                            continue
                
                if isinstance(parallel_line, LineString):
                    flight_lines.append(parallel_line)
            except Exception as e:
                self.logger.warning(f"生成平行线 {i} 时出错: {e}")
                continue
        
        return flight_lines
    
    def _generate_zigzag_flight(
        self, 
        path_line: LineString, 
        mission_input: StripMissionInput
    ) -> List[LineString]:
        """生成之字形飞行航线。"""
        # 先生成平行线
        parallel_lines = self._generate_parallel_lines_flight(path_line, mission_input)
        
        if len(parallel_lines) <= 1:
            return parallel_lines
        
        # 连接平行线形成之字形
        zigzag_lines = []
        
        for i, line in enumerate(parallel_lines):
            if i % 2 == 1:  # 奇数线反向
                coords = list(line.coords)
                coords.reverse()
                line = LineString(coords)
            
            zigzag_lines.append(line)
            
            # 添加连接线（除了最后一条）
            if i < len(parallel_lines) - 1:
                current_end = line.coords[-1]
                next_start = parallel_lines[i + 1].coords[0]
                if (i + 1) % 2 == 1:  # 下一条线需要反向
                    next_start = parallel_lines[i + 1].coords[-1]
                
                connection_line = LineString([current_end, next_start])
                zigzag_lines.append(connection_line)
        
        return zigzag_lines
    
    def _generate_back_and_forth_flight(
        self, 
        path_line: LineString, 
        mission_input: StripMissionInput
    ) -> List[LineString]:
        """生成往返飞行航线。"""
        flight_lines = []
        
        # 正向飞行
        flight_lines.append(path_line)
        
        # 反向飞行
        coords = list(path_line.coords)
        coords.reverse()
        reverse_line = LineString(coords)
        flight_lines.append(reverse_line)
        
        return flight_lines
    
    def _flight_lines_to_waypoints(
        self, 
        flight_lines: List[LineString], 
        mission_input: StripMissionInput
    ) -> List[Waypoint]:
        """将航线转换为航点。"""
        waypoints = []
        waypoint_index = 0
        
        for line in flight_lines:
            # 根据航线长度和重叠率计算航点间距
            line_length = self._calculate_line_length(line)
            
            # 计算相机覆盖长度
            camera_specs = self._get_camera_specs(mission_input.aircraft_type)
            ground_length = self._calculate_ground_coverage_length(
                mission_input.flight_height,
                camera_specs,
                mission_input.gimbal_pitch
            )
            
            # 计算航点间距
            overlap_factor = (100 - mission_input.overlap_rate) / 100
            waypoint_spacing = ground_length * overlap_factor
            
            # 计算航点数量
            num_waypoints = max(2, int(line_length / waypoint_spacing) + 1)
            
            # 生成航点
            for i in range(num_waypoints):
                # 计算沿线的位置比例
                ratio = i / (num_waypoints - 1) if num_waypoints > 1 else 0
                
                # 在线上插值获取坐标
                point = line.interpolate(ratio, normalized=True)
                
                # 获取高度
                altitude = mission_input.flight_height
                if mission_input.adaptive_height:
                    # 简单的高度自适应逻辑
                    altitude += random.uniform(-10, 10)
                
                coordinates = Coordinates(
                    latitude=point.y,
                    longitude=point.x,
                    altitude=altitude
                )
                
                waypoint = Waypoint(
                    index=waypoint_index,
                    coordinates=coordinates,
                    speed=mission_input.flight_speed,
                    gimbal_pitch_angle=mission_input.gimbal_pitch,
                    use_global_height=True,
                    use_global_speed=True
                )
                
                waypoints.append(waypoint)
                waypoint_index += 1
        
        return waypoints
    
    def _add_photo_actions(
        self, 
        waypoints: List[Waypoint], 
        mission_input: StripMissionInput
    ) -> List[Waypoint]:
        """添加拍摄动作。"""
        if not waypoints:
            return waypoints
        
        # 计算拍摄间隔
        camera_specs = self._get_camera_specs(mission_input.aircraft_type)
        
        if mission_input.shoot_mode == "time":
            # 基于重叠率计算时间间隔
            ground_length = self._calculate_ground_coverage_length(
                mission_input.flight_height,
                camera_specs,
                mission_input.gimbal_pitch
            )
            
            overlap_factor = (100 - mission_input.overlap_rate) / 100
            photo_spacing = ground_length * overlap_factor
            photo_interval = photo_spacing / mission_input.flight_speed
            photo_interval = max(photo_interval, 1.0)  # 最小1秒间隔
            
            # 为每个航点添加时间触发的拍摄动作
            for i, waypoint in enumerate(waypoints):
                photo_action = Action(
                    action_id=0,
                    action_type=ActionType.TAKE_PHOTO,
                    parameters={
                        "suffix": f"strip_{i}",
                        "payload_position": 0,
                        "use_global_lens": 1
                    }
                )
                
                action_group = ActionGroup(
                    group_id=0,
                    start_index=i,
                    end_index=i,
                    trigger=ActionTrigger(
                        trigger_type=ActionTriggerType.MULTIPLE_TIMING,
                        trigger_param=photo_interval
                    ),
                    actions=[photo_action]
                )
                
                waypoint.action_groups = [action_group]
        
        elif mission_input.shoot_mode == "distance":
            # 基于距离触发拍摄
            ground_length = self._calculate_ground_coverage_length(
                mission_input.flight_height,
                camera_specs,
                mission_input.gimbal_pitch
            )
            
            overlap_factor = (100 - mission_input.overlap_rate) / 100
            distance_interval = ground_length * overlap_factor
            
            # 为每个航点添加距离触发的拍摄动作
            for i, waypoint in enumerate(waypoints):
                photo_action = Action(
                    action_id=0,
                    action_type=ActionType.TAKE_PHOTO,
                    parameters={
                        "suffix": f"strip_{i}",
                        "payload_position": 0,
                        "use_global_lens": 1
                    }
                )
                
                action_group = ActionGroup(
                    group_id=0,
                    start_index=i,
                    end_index=i,
                    trigger=ActionTrigger(
                        trigger_type=ActionTriggerType.MULTIPLE_DISTANCE,
                        trigger_param=distance_interval
                    ),
                    actions=[photo_action]
                )
                
                waypoint.action_groups = [action_group]
        
        return waypoints
    
    def _calculate_mission_statistics(
        self, 
        flight_path: FlightPath, 
        strip_boundary: Polygon, 
        mission_input: StripMissionInput
    ) -> Dict[str, Any]:
        """计算任务统计信息。"""
        # 计算总飞行距离
        total_distance = 0.0
        for i in range(len(flight_path.waypoints) - 1):
            wp1 = flight_path.waypoints[i]
            wp2 = flight_path.waypoints[i + 1]
            distance = self.geometry_calc.haversine_distance(wp1.coordinates, wp2.coordinates)
            total_distance += distance
        
        # 计算飞行时间
        estimated_flight_time = total_distance / mission_input.flight_speed / 60  # 转换为分钟
        
        # 计算航带长度
        path_line = self._create_path_line(mission_input.path_points)
        strip_length = self._calculate_line_length(path_line)
        
        # 计算覆盖面积
        coverage_area = strip_boundary.area * (111000 ** 2) / 10000  # 转换为公顷
        
        # 计算拍摄参数
        camera_specs = self._get_camera_specs(mission_input.aircraft_type)
        ground_length = self._calculate_ground_coverage_length(
            mission_input.flight_height,
            camera_specs,
            mission_input.gimbal_pitch
        )
        
        overlap_factor = (100 - mission_input.overlap_rate) / 100
        photo_spacing = ground_length * overlap_factor
        
        if mission_input.shoot_mode == "time":
            photo_interval = photo_spacing / mission_input.flight_speed
            photo_interval = max(photo_interval, 1.0)
        else:
            photo_interval = photo_spacing
        
        # 估算照片数量
        estimated_photos = int(total_distance / photo_spacing) if photo_spacing > 0 else 0
        
        # 计算地面分辨率
        ground_resolution = self._calculate_ground_resolution(
            mission_input.flight_height,
            camera_specs
        )
        
        return {
            "total_distance": round(total_distance, 2),
            "estimated_flight_time": round(estimated_flight_time, 1),
            "strip_length": round(strip_length, 2),
            "coverage_area": round(coverage_area, 2),
            "photo_interval": round(photo_interval, 2),
            "estimated_photos": estimated_photos,
            "ground_resolution": round(ground_resolution, 2),
            "waypoint_count": len(flight_path.waypoints)
        }
    
    def _get_camera_specs(self, aircraft_type: str) -> Dict[str, float]:
        """获取相机规格。"""
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
    
    def _calculate_ground_coverage_width(
        self, 
        flight_height: float, 
        camera_specs: Dict[str, float],
        gimbal_pitch: float
    ) -> float:
        """计算地面覆盖宽度。"""
        # 考虑云台角度的影响
        pitch_rad = math.radians(abs(gimbal_pitch))
        effective_height = flight_height / math.cos(pitch_rad) if pitch_rad < math.pi/2 else flight_height
        
        ground_width = (camera_specs["sensor_width"] * effective_height) / camera_specs["focal_length"]
        return ground_width
    
    def _calculate_ground_coverage_length(
        self, 
        flight_height: float, 
        camera_specs: Dict[str, float],
        gimbal_pitch: float
    ) -> float:
        """计算地面覆盖长度。"""
        # 考虑云台角度的影响
        pitch_rad = math.radians(abs(gimbal_pitch))
        effective_height = flight_height / math.cos(pitch_rad) if pitch_rad < math.pi/2 else flight_height
        
        ground_length = (camera_specs["sensor_height"] * effective_height) / camera_specs["focal_length"]
        return ground_length
    
    def _calculate_ground_resolution(
        self, 
        flight_height: float, 
        camera_specs: Dict[str, float]
    ) -> float:
        """计算地面分辨率(cm/pixel)。"""
        ground_resolution = (camera_specs["sensor_width"] * flight_height) / (
            camera_specs["focal_length"] * camera_specs["image_width"]
        ) * 100  # 转换为cm/pixel
        
        return ground_resolution
    
    def _calculate_line_length(self, line: LineString) -> float:
        """计算线的长度（米）。"""
        # 简化计算：将度转换为米
        total_length = 0.0
        coords = list(line.coords)
        
        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i + 1]
            
            # 使用Haversine公式计算距离
            lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
            lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
            
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            
            a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            distance = 6371000 * c  # 地球半径6371km
            
            total_length += distance
        
        return total_length
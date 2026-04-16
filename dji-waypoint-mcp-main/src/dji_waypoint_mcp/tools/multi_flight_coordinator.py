"""
多航线协调和管理工具。
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
from .oblique_missions import ObliqueAngle, ObliqueDirection
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
from ..utils.geometry import geometry_calculator
from ..utils.coverage_analysis import coverage_analyzer
from ..config import settings


class FlightPriority(str, Enum):
    """航线优先级。"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FlightSequenceMode(str, Enum):
    """航线执行顺序模式。"""
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"     # 并行执行
    OPTIMIZED = "optimized"   # 优化顺序


@dataclass
class FlightConfiguration:
    """单个航线配置。"""
    flight_id: str
    flight_path: FlightPath
    priority: FlightPriority
    estimated_duration: float
    battery_consumption: float
    photo_count: int
    coverage_area: float
    gimbal_angles: Dict[str, float]
    metadata: Dict[str, Any]


class MultiFlightInput(BaseModel):
    """多航线协调输入参数。"""
    flight_configurations: List[Dict[str, Any]] = Field(..., min_items=1, description="航线配置列表")
    sequence_mode: FlightSequenceMode = Field(default=FlightSequenceMode.OPTIMIZED, description="执行顺序模式")
    max_flight_time: float = Field(default=25.0, ge=5, le=30, description="单次飞行最大时间(分钟)")
    battery_reserve: float = Field(default=20.0, ge=10, le=50, description="电池预留百分比")
    transition_time: float = Field(default=2.0, ge=0, le=10, description="航线间转换时间(分钟)")
    quality_threshold: float = Field(default=0.8, ge=0.5, le=1.0, description="质量控制阈值")
    optimize_battery_usage: bool = Field(default=True, description="优化电池使用")
    merge_compatible_flights: bool = Field(default=False, description="合并兼容的航线")
    
    @validator('flight_configurations')
    def validate_flight_configurations(cls, v):
        """验证航线配置。"""
        if not v:
            raise ValueError("至少需要一个航线配置")
        return v


class MultiFlightCoordinator(BaseTool, ValidationMixin):
    """多航线协调工具。"""
    
    def __init__(self):
        """初始化多航线协调器。"""
        super().__init__()
        self.geometry_calc = geometry_calculator
    
    def get_tool_definition(self) -> Tool:
        """获取MCP工具定义。"""
        return Tool(
            name="coordinate_multi_flights",
            description="协调和管理多条航线的执行顺序和参数配置",
            inputSchema={
                "type": "object",
                "properties": {
                    "flight_configurations": {
                        "type": "array",
                        "description": "航线配置列表",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "flight_id": {"type": "string", "description": "航线唯一标识"},
                                "flight_path": {"type": "object", "description": "航线路径数据"},
                                "priority": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                    "default": "medium"
                                },
                                "gimbal_pitch": {"type": "number", "minimum": -90, "maximum": 0},
                                "gimbal_yaw": {"type": "number", "minimum": -180, "maximum": 180},
                                "photo_interval": {"type": "number", "minimum": 0.5, "maximum": 10},
                                "flight_speed": {"type": "number", "minimum": 1, "maximum": 15}
                            },
                            "required": ["flight_id", "flight_path"]
                        }
                    },
                    "sequence_mode": {
                        "type": "string",
                        "enum": ["sequential", "parallel", "optimized"],
                        "default": "optimized",
                        "description": "执行顺序模式"
                    },
                    "max_flight_time": {
                        "type": "number",
                        "minimum": 5,
                        "maximum": 30,
                        "default": 25.0,
                        "description": "单次飞行最大时间(分钟)"
                    },
                    "battery_reserve": {
                        "type": "number",
                        "minimum": 10,
                        "maximum": 50,
                        "default": 20.0,
                        "description": "电池预留百分比"
                    },
                    "transition_time": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 10,
                        "default": 2.0,
                        "description": "航线间转换时间(分钟)"
                    },
                    "quality_threshold": {
                        "type": "number",
                        "minimum": 0.5,
                        "maximum": 1.0,
                        "default": 0.8,
                        "description": "质量控制阈值"
                    },
                    "optimize_battery_usage": {
                        "type": "boolean",
                        "default": True,
                        "description": "优化电池使用"
                    },
                    "merge_compatible_flights": {
                        "type": "boolean",
                        "default": False,
                        "description": "合并兼容的航线"
                    }
                },
                "required": ["flight_configurations"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行多航线协调。"""
        try:
            # 验证输入参数
            multi_flight_input = MultiFlightInput(**arguments)
            
            self.logger.info(f"协调 {len(multi_flight_input.flight_configurations)} 条航线")
            
            # 解析航线配置
            flight_configs = self._parse_flight_configurations(
                multi_flight_input.flight_configurations
            )
            
            # 验证航线兼容性
            compatibility_report = self._analyze_flight_compatibility(flight_configs)
            
            # 合并兼容的航线（如果启用）
            if multi_flight_input.merge_compatible_flights:
                flight_configs = self._merge_compatible_flights(
                    flight_configs, 
                    compatibility_report
                )
            
            # 优化航线顺序
            optimized_sequence = self._optimize_flight_sequence(
                flight_configs,
                multi_flight_input.sequence_mode,
                multi_flight_input.max_flight_time,
                multi_flight_input.battery_reserve
            )
            
            # 计算电池使用计划
            battery_plan = self._calculate_battery_plan(
                optimized_sequence,
                multi_flight_input.max_flight_time,
                multi_flight_input.battery_reserve,
                multi_flight_input.transition_time
            )
            
            # 执行质量控制检查
            quality_report = self._perform_quality_control(
                flight_configs,
                multi_flight_input.quality_threshold
            )
            
            # 生成协调计划
            coordination_plan = self._generate_coordination_plan(
                optimized_sequence,
                battery_plan,
                quality_report,
                multi_flight_input
            )
            
            # 计算总体统计
            overall_stats = self._calculate_overall_statistics(
                flight_configs,
                coordination_plan
            )
            
            # 准备响应数据
            response_data = {
                "coordination_plan": coordination_plan,
                "flight_sequence": [
                    {
                        "flight_id": config.flight_id,
                        "priority": config.priority,
                        "estimated_duration": config.estimated_duration,
                        "battery_consumption": config.battery_consumption,
                        "photo_count": config.photo_count,
                        "coverage_area": config.coverage_area,
                        "gimbal_angles": config.gimbal_angles
                    }
                    for config in optimized_sequence
                ],
                "battery_plan": battery_plan,
                "quality_report": quality_report,
                "compatibility_report": compatibility_report,
                "overall_statistics": overall_stats
            }
            
            return self.format_success_response(
                f"成功协调 {len(flight_configs)} 条航线，生成 {len(coordination_plan['flight_batches'])} 个飞行批次",
                response_data
            )
            
        except ValidationError as e:
            self.logger.error(f"多航线协调验证错误: {e}")
            return self.format_error_response(f"输入参数无效: {e}")
        
        except ValueError as e:
            self.logger.error(f"多航线协调值错误: {e}")
            return self.format_error_response(str(e))
        
        except Exception as e:
            self.logger.error(f"多航线协调意外错误: {e}", exc_info=True)
            return self.format_error_response(f"多航线协调失败: {e}")
    
    def _parse_flight_configurations(
        self, 
        config_data: List[Dict[str, Any]]
    ) -> List[FlightConfiguration]:
        """解析航线配置数据。"""
        flight_configs = []
        
        for i, config in enumerate(config_data):
            try:
                # 解析航线路径
                flight_path_data = config.get("flight_path", {})
                waypoints_data = flight_path_data.get("waypoints", [])
                
                # 创建航点列表
                waypoints = []
                for wp_data in waypoints_data:
                    coords_data = wp_data.get("coordinates", {})
                    coordinates = Coordinates(
                        latitude=coords_data.get("latitude", 0.0),
                        longitude=coords_data.get("longitude", 0.0),
                        altitude=coords_data.get("altitude", 100.0)
                    )
                    
                    waypoint = Waypoint(
                        index=wp_data.get("index", 0),
                        coordinates=coordinates,
                        speed=wp_data.get("speed", 5.0),
                        gimbal_pitch_angle=wp_data.get("gimbal_pitch_angle", -90.0)
                    )
                    waypoints.append(waypoint)
                
                # 创建航线路径
                flight_path = FlightPath(
                    waypoints=waypoints,
                    global_speed=flight_path_data.get("global_speed", 5.0),
                    global_height=flight_path_data.get("global_height", 100.0),
                    height_mode=HeightMode.EGM96
                )
                
                # 计算航线统计
                stats = self._calculate_flight_statistics(flight_path, config)
                
                # 创建航线配置
                flight_config = FlightConfiguration(
                    flight_id=config.get("flight_id", f"flight_{i}"),
                    flight_path=flight_path,
                    priority=FlightPriority(config.get("priority", "medium")),
                    estimated_duration=stats["duration"],
                    battery_consumption=stats["battery_consumption"],
                    photo_count=stats["photo_count"],
                    coverage_area=stats["coverage_area"],
                    gimbal_angles={
                        "pitch": config.get("gimbal_pitch", -90.0),
                        "yaw": config.get("gimbal_yaw", 0.0)
                    },
                    metadata=config.get("metadata", {})
                )
                
                flight_configs.append(flight_config)
                
            except Exception as e:
                self.logger.error(f"解析航线配置 {i} 时出错: {e}")
                raise ValueError(f"航线配置 {i} 解析失败: {e}")
        
        return flight_configs
    
    def _calculate_flight_statistics(
        self, 
        flight_path: FlightPath, 
        config: Dict[str, Any]
    ) -> Dict[str, float]:
        """计算单个航线的统计信息。"""
        # 计算总飞行距离
        total_distance = 0.0
        for i in range(len(flight_path.waypoints) - 1):
            wp1 = flight_path.waypoints[i]
            wp2 = flight_path.waypoints[i + 1]
            distance = self.geometry_calc.haversine_distance(wp1.coordinates, wp2.coordinates)
            total_distance += distance
        
        # 计算飞行时间
        flight_speed = config.get("flight_speed", flight_path.global_speed)
        duration = total_distance / flight_speed / 60  # 转换为分钟
        
        # 估算电池消耗（基于飞行时间和距离）
        base_consumption = duration * 3.5  # 每分钟约3.5%电量
        distance_factor = total_distance / 1000 * 2  # 每公里额外2%
        battery_consumption = min(base_consumption + distance_factor, 80.0)  # 最大80%
        
        # 估算拍照数量
        photo_interval = config.get("photo_interval", 2.0)
        photo_count = int(duration * 60 / photo_interval) if photo_interval > 0 else 0
        
        # 估算覆盖面积（简化计算）
        coverage_area = total_distance * 200 / 10000  # 假设200米宽度，转换为公顷
        
        return {
            "duration": round(duration, 2),
            "battery_consumption": round(battery_consumption, 1),
            "photo_count": photo_count,
            "coverage_area": round(coverage_area, 2),
            "total_distance": round(total_distance, 2)
        }
    
    def _analyze_flight_compatibility(
        self, 
        flight_configs: List[FlightConfiguration]
    ) -> Dict[str, Any]:
        """分析航线兼容性。"""
        compatibility_matrix = {}
        compatible_groups = []
        conflicts = []
        
        for i, config1 in enumerate(flight_configs):
            compatibility_matrix[config1.flight_id] = {}
            
            for j, config2 in enumerate(flight_configs):
                if i == j:
                    continue
                
                # 检查兼容性
                compatibility_score = self._calculate_compatibility_score(config1, config2)
                compatibility_matrix[config1.flight_id][config2.flight_id] = compatibility_score
                
                # 记录冲突
                if compatibility_score < 0.5:
                    conflicts.append({
                        "flight1": config1.flight_id,
                        "flight2": config2.flight_id,
                        "score": compatibility_score,
                        "issues": self._identify_compatibility_issues(config1, config2)
                    })
        
        # 识别兼容组
        compatible_groups = self._find_compatible_groups(flight_configs, compatibility_matrix)
        
        return {
            "compatibility_matrix": compatibility_matrix,
            "compatible_groups": compatible_groups,
            "conflicts": conflicts,
            "overall_compatibility": self._calculate_overall_compatibility(compatibility_matrix)
        }
    
    def _calculate_compatibility_score(
        self, 
        config1: FlightConfiguration, 
        config2: FlightConfiguration
    ) -> float:
        """计算两个航线的兼容性分数。"""
        score = 1.0
        
        # 检查云台角度差异
        pitch_diff = abs(config1.gimbal_angles["pitch"] - config2.gimbal_angles["pitch"])
        yaw_diff = abs(config1.gimbal_angles["yaw"] - config2.gimbal_angles["yaw"])
        
        if pitch_diff > 10:
            score -= 0.2
        if yaw_diff > 30:
            score -= 0.2
        
        # 检查飞行高度差异
        height1 = config1.flight_path.global_height
        height2 = config2.flight_path.global_height
        height_diff = abs(height1 - height2)
        
        if height_diff > 20:
            score -= 0.2
        
        # 检查飞行速度差异
        speed1 = config1.flight_path.global_speed
        speed2 = config2.flight_path.global_speed
        speed_diff = abs(speed1 - speed2)
        
        if speed_diff > 2:
            score -= 0.1
        
        # 检查覆盖区域重叠
        overlap_score = self._calculate_coverage_overlap(config1, config2)
        if overlap_score > 0.8:
            score -= 0.3  # 高重叠度降低兼容性
        
        return max(score, 0.0)
    
    def _identify_compatibility_issues(
        self, 
        config1: FlightConfiguration, 
        config2: FlightConfiguration
    ) -> List[str]:
        """识别兼容性问题。"""
        issues = []
        
        # 云台角度冲突
        pitch_diff = abs(config1.gimbal_angles["pitch"] - config2.gimbal_angles["pitch"])
        if pitch_diff > 10:
            issues.append(f"云台俯仰角差异过大: {pitch_diff:.1f}度")
        
        yaw_diff = abs(config1.gimbal_angles["yaw"] - config2.gimbal_angles["yaw"])
        if yaw_diff > 30:
            issues.append(f"云台偏航角差异过大: {yaw_diff:.1f}度")
        
        # 飞行参数冲突
        height_diff = abs(config1.flight_path.global_height - config2.flight_path.global_height)
        if height_diff > 20:
            issues.append(f"飞行高度差异过大: {height_diff:.1f}米")
        
        speed_diff = abs(config1.flight_path.global_speed - config2.flight_path.global_speed)
        if speed_diff > 2:
            issues.append(f"飞行速度差异过大: {speed_diff:.1f}m/s")
        
        # 覆盖区域重叠
        overlap_score = self._calculate_coverage_overlap(config1, config2)
        if overlap_score > 0.8:
            issues.append(f"覆盖区域重叠度过高: {overlap_score:.1%}")
        
        return issues
    
    def _calculate_coverage_overlap(
        self, 
        config1: FlightConfiguration, 
        config2: FlightConfiguration
    ) -> float:
        """计算两个航线的覆盖区域重叠度。"""
        # 简化计算：基于航点位置的重叠度
        waypoints1 = config1.flight_path.waypoints
        waypoints2 = config2.flight_path.waypoints
        
        if not waypoints1 or not waypoints2:
            return 0.0
        
        # 计算航点间的最小距离
        min_distances = []
        for wp1 in waypoints1:
            distances = [
                self.geometry_calc.haversine_distance(wp1.coordinates, wp2.coordinates)
                for wp2 in waypoints2
            ]
            min_distances.append(min(distances))
        
        # 基于最小距离计算重叠度
        avg_min_distance = sum(min_distances) / len(min_distances)
        overlap_threshold = 500  # 500米内认为有重叠
        
        if avg_min_distance < overlap_threshold:
            return 1.0 - (avg_min_distance / overlap_threshold)
        else:
            return 0.0
    
    def _find_compatible_groups(
        self, 
        flight_configs: List[FlightConfiguration],
        compatibility_matrix: Dict[str, Dict[str, float]]
    ) -> List[List[str]]:
        """找到兼容的航线组。"""
        groups = []
        processed = set()
        
        for config in flight_configs:
            if config.flight_id in processed:
                continue
            
            # 找到与当前航线兼容的所有航线
            compatible_flights = [config.flight_id]
            
            for other_id, score in compatibility_matrix[config.flight_id].items():
                if score >= 0.7 and other_id not in processed:
                    compatible_flights.append(other_id)
            
            if len(compatible_flights) > 1:
                groups.append(compatible_flights)
                processed.update(compatible_flights)
            else:
                processed.add(config.flight_id)
        
        return groups
    
    def _calculate_overall_compatibility(
        self, 
        compatibility_matrix: Dict[str, Dict[str, float]]
    ) -> float:
        """计算整体兼容性分数。"""
        all_scores = []
        
        for flight_id, scores in compatibility_matrix.items():
            all_scores.extend(scores.values())
        
        if not all_scores:
            return 1.0
        
        return sum(all_scores) / len(all_scores)
    
    def _merge_compatible_flights(
        self, 
        flight_configs: List[FlightConfiguration],
        compatibility_report: Dict[str, Any]
    ) -> List[FlightConfiguration]:
        """合并兼容的航线。"""
        merged_configs = []
        processed_ids = set()
        
        # 处理兼容组
        for group in compatibility_report["compatible_groups"]:
            if len(group) > 1:
                # 合并组内的航线
                group_configs = [
                    config for config in flight_configs 
                    if config.flight_id in group
                ]
                
                merged_config = self._merge_flight_group(group_configs)
                merged_configs.append(merged_config)
                processed_ids.update(group)
        
        # 添加未处理的单独航线
        for config in flight_configs:
            if config.flight_id not in processed_ids:
                merged_configs.append(config)
        
        return merged_configs
    
    def _merge_flight_group(
        self, 
        group_configs: List[FlightConfiguration]
    ) -> FlightConfiguration:
        """合并一组兼容的航线。"""
        if len(group_configs) == 1:
            return group_configs[0]
        
        # 使用第一个航线作为基础
        base_config = group_configs[0]
        
        # 合并航点
        all_waypoints = []
        waypoint_index = 0
        
        for config in group_configs:
            for wp in config.flight_path.waypoints:
                new_wp = Waypoint(
                    index=waypoint_index,
                    coordinates=wp.coordinates,
                    speed=wp.speed,
                    gimbal_pitch_angle=wp.gimbal_pitch_angle,
                    use_global_height=wp.use_global_height,
                    use_global_speed=wp.use_global_speed,
                    action_groups=wp.action_groups
                )
                all_waypoints.append(new_wp)
                waypoint_index += 1
        
        # 创建合并的航线路径
        merged_flight_path = FlightPath(
            waypoints=all_waypoints,
            global_speed=base_config.flight_path.global_speed,
            global_height=base_config.flight_path.global_height,
            height_mode=base_config.flight_path.height_mode,
            global_turn_mode=base_config.flight_path.global_turn_mode
        )
        
        # 计算合并后的统计信息
        total_duration = sum(config.estimated_duration for config in group_configs)
        total_battery = sum(config.battery_consumption for config in group_configs)
        total_photos = sum(config.photo_count for config in group_configs)
        total_coverage = sum(config.coverage_area for config in group_configs)
        
        # 创建合并的配置
        merged_config = FlightConfiguration(
            flight_id=f"merged_{'_'.join(config.flight_id for config in group_configs)}",
            flight_path=merged_flight_path,
            priority=max(config.priority for config in group_configs),
            estimated_duration=total_duration,
            battery_consumption=min(total_battery, 80.0),  # 限制最大电池消耗
            photo_count=total_photos,
            coverage_area=total_coverage,
            gimbal_angles=base_config.gimbal_angles,
            metadata={
                "merged_from": [config.flight_id for config in group_configs],
                "merge_timestamp": "auto_merged"
            }
        )
        
        return merged_config
    
    def _optimize_flight_sequence(
        self,
        flight_configs: List[FlightConfiguration],
        sequence_mode: FlightSequenceMode,
        max_flight_time: float,
        battery_reserve: float
    ) -> List[FlightConfiguration]:
        """优化航线执行顺序。"""
        if sequence_mode == FlightSequenceMode.SEQUENTIAL:
            # 按优先级排序
            return sorted(flight_configs, key=lambda x: (x.priority.value, x.estimated_duration))
        
        elif sequence_mode == FlightSequenceMode.PARALLEL:
            # 按电池消耗排序，便于并行执行
            return sorted(flight_configs, key=lambda x: x.battery_consumption)
        
        elif sequence_mode == FlightSequenceMode.OPTIMIZED:
            # 使用启发式算法优化顺序
            return self._heuristic_optimization(flight_configs, max_flight_time, battery_reserve)
        
        else:
            return flight_configs
    
    def _heuristic_optimization(
        self,
        flight_configs: List[FlightConfiguration],
        max_flight_time: float,
        battery_reserve: float
    ) -> List[FlightConfiguration]:
        """使用启发式算法优化航线顺序。"""
        # 计算每个航线的优化分数
        scored_configs = []
        
        for config in flight_configs:
            # 综合考虑优先级、时间、电池消耗
            priority_score = {"high": 3, "medium": 2, "low": 1}[config.priority.value]
            time_score = max_flight_time / max(config.estimated_duration, 1)
            battery_score = (100 - battery_reserve) / max(config.battery_consumption, 1)
            
            # 加权综合分数
            total_score = priority_score * 0.4 + time_score * 0.3 + battery_score * 0.3
            
            scored_configs.append((config, total_score))
        
        # 按分数排序
        scored_configs.sort(key=lambda x: x[1], reverse=True)
        
        return [config for config, score in scored_configs]
    
    def _calculate_battery_plan(
        self,
        flight_sequence: List[FlightConfiguration],
        max_flight_time: float,
        battery_reserve: float,
        transition_time: float
    ) -> Dict[str, Any]:
        """计算电池使用计划。"""
        battery_plan = {
            "flight_batches": [],
            "total_batteries_needed": 0,
            "total_flight_time": 0,
            "battery_changes": 0
        }
        
        current_battery = 100.0
        current_batch = []
        current_batch_time = 0.0
        batch_number = 1
        
        for config in flight_sequence:
            # 检查是否需要更换电池
            required_battery = config.battery_consumption + battery_reserve
            
            if (current_battery < required_battery or 
                current_batch_time + config.estimated_duration > max_flight_time):
                
                # 完成当前批次
                if current_batch:
                    battery_plan["flight_batches"].append({
                        "batch_number": batch_number,
                        "flights": [f.flight_id for f in current_batch],
                        "total_time": round(current_batch_time, 2),
                        "battery_usage": round(100 - current_battery, 1),
                        "transition_time": transition_time if batch_number > 1 else 0
                    })
                    batch_number += 1
                
                # 开始新批次
                current_battery = 100.0
                current_batch = []
                current_batch_time = 0.0
                battery_plan["battery_changes"] += 1
            
            # 添加到当前批次
            current_batch.append(config)
            current_batch_time += config.estimated_duration
            current_battery -= config.battery_consumption
        
        # 完成最后一个批次
        if current_batch:
            battery_plan["flight_batches"].append({
                "batch_number": batch_number,
                "flights": [f.flight_id for f in current_batch],
                "total_time": round(current_batch_time, 2),
                "battery_usage": round(100 - current_battery, 1),
                "transition_time": transition_time if batch_number > 1 else 0
            })
        
        # 计算总体统计
        battery_plan["total_batteries_needed"] = len(battery_plan["flight_batches"])
        battery_plan["total_flight_time"] = sum(
            batch["total_time"] for batch in battery_plan["flight_batches"]
        )
        
        return battery_plan
    
    def _perform_quality_control(
        self,
        flight_configs: List[FlightConfiguration],
        quality_threshold: float
    ) -> Dict[str, Any]:
        """执行质量控制检查。"""
        quality_report = {
            "overall_quality": 0.0,
            "flight_quality_scores": {},
            "quality_issues": [],
            "recommendations": []
        }
        
        quality_scores = []
        
        for config in flight_configs:
            # 计算单个航线的质量分数
            quality_score = self._calculate_flight_quality(config)
            quality_scores.append(quality_score)
            quality_report["flight_quality_scores"][config.flight_id] = quality_score
            
            # 检查质量问题
            if quality_score < quality_threshold:
                issues = self._identify_quality_issues(config, quality_score)
                quality_report["quality_issues"].extend(issues)
        
        # 计算整体质量
        quality_report["overall_quality"] = sum(quality_scores) / len(quality_scores)
        
        # 生成建议
        quality_report["recommendations"] = self._generate_quality_recommendations(
            flight_configs, quality_report
        )
        
        return quality_report
    
    def _calculate_flight_quality(self, config: FlightConfiguration) -> float:
        """计算单个航线的质量分数。"""
        quality_score = 1.0
        
        # 检查航点数量
        waypoint_count = len(config.flight_path.waypoints)
        if waypoint_count < 4:
            quality_score -= 0.2
        elif waypoint_count > 200:
            quality_score -= 0.1
        
        # 检查飞行时间
        if config.estimated_duration < 2:
            quality_score -= 0.1
        elif config.estimated_duration > 25:
            quality_score -= 0.2
        
        # 检查电池消耗
        if config.battery_consumption > 70:
            quality_score -= 0.2
        elif config.battery_consumption < 10:
            quality_score -= 0.1
        
        # 检查覆盖面积
        if config.coverage_area < 1:
            quality_score -= 0.1
        
        # 检查云台角度合理性
        pitch = config.gimbal_angles["pitch"]
        if pitch > -30 or pitch < -90:
            quality_score -= 0.1
        
        return max(quality_score, 0.0)
    
    def _identify_quality_issues(
        self, 
        config: FlightConfiguration, 
        quality_score: float
    ) -> List[Dict[str, Any]]:
        """识别质量问题。"""
        issues = []
        
        # 航点数量问题
        waypoint_count = len(config.flight_path.waypoints)
        if waypoint_count < 4:
            issues.append({
                "flight_id": config.flight_id,
                "type": "waypoint_count",
                "severity": "high",
                "message": f"航点数量过少: {waypoint_count}个"
            })
        elif waypoint_count > 200:
            issues.append({
                "flight_id": config.flight_id,
                "type": "waypoint_count",
                "severity": "medium",
                "message": f"航点数量过多: {waypoint_count}个"
            })
        
        # 飞行时间问题
        if config.estimated_duration > 25:
            issues.append({
                "flight_id": config.flight_id,
                "type": "flight_time",
                "severity": "high",
                "message": f"飞行时间过长: {config.estimated_duration:.1f}分钟"
            })
        
        # 电池消耗问题
        if config.battery_consumption > 70:
            issues.append({
                "flight_id": config.flight_id,
                "type": "battery_consumption",
                "severity": "high",
                "message": f"电池消耗过高: {config.battery_consumption:.1f}%"
            })
        
        return issues
    
    def _generate_quality_recommendations(
        self,
        flight_configs: List[FlightConfiguration],
        quality_report: Dict[str, Any]
    ) -> List[str]:
        """生成质量改进建议。"""
        recommendations = []
        
        # 基于整体质量给出建议
        if quality_report["overall_quality"] < 0.7:
            recommendations.append("整体航线质量较低，建议重新规划部分航线")
        
        # 基于具体问题给出建议
        for issue in quality_report["quality_issues"]:
            if issue["type"] == "waypoint_count" and issue["severity"] == "high":
                recommendations.append(f"航线 {issue['flight_id']} 航点过少，建议增加中间航点")
            elif issue["type"] == "flight_time" and issue["severity"] == "high":
                recommendations.append(f"航线 {issue['flight_id']} 飞行时间过长，建议分割为多个子航线")
            elif issue["type"] == "battery_consumption" and issue["severity"] == "high":
                recommendations.append(f"航线 {issue['flight_id']} 电池消耗过高，建议降低飞行速度或减少航点")
        
        # 基于航线数量给出建议
        if len(flight_configs) > 5:
            recommendations.append("航线数量较多，建议考虑合并兼容的航线以提高效率")
        
        return recommendations
    
    def _generate_coordination_plan(
        self,
        optimized_sequence: List[FlightConfiguration],
        battery_plan: Dict[str, Any],
        quality_report: Dict[str, Any],
        multi_flight_input: MultiFlightInput
    ) -> Dict[str, Any]:
        """生成协调计划。"""
        coordination_plan = {
            "execution_mode": multi_flight_input.sequence_mode.value,
            "flight_batches": battery_plan["flight_batches"],
            "total_execution_time": 0.0,
            "quality_status": "good" if quality_report["overall_quality"] >= 0.8 else "warning",
            "execution_steps": [],
            "safety_checks": [],
            "contingency_plans": []
        }
        
        # 生成执行步骤
        total_time = 0.0
        for i, batch in enumerate(battery_plan["flight_batches"]):
            step_time = batch["total_time"] + batch.get("transition_time", 0)
            total_time += step_time
            
            coordination_plan["execution_steps"].append({
                "step": i + 1,
                "action": "execute_flight_batch",
                "batch_number": batch["batch_number"],
                "flights": batch["flights"],
                "estimated_time": batch["total_time"],
                "transition_time": batch.get("transition_time", 0),
                "cumulative_time": round(total_time, 2)
            })
            
            # 添加电池更换步骤（除了最后一个批次）
            if i < len(battery_plan["flight_batches"]) - 1:
                coordination_plan["execution_steps"].append({
                    "step": f"{i + 1}.5",
                    "action": "change_battery",
                    "estimated_time": multi_flight_input.transition_time,
                    "cumulative_time": round(total_time + multi_flight_input.transition_time, 2)
                })
                total_time += multi_flight_input.transition_time
        
        coordination_plan["total_execution_time"] = round(total_time, 2)
        
        # 生成安全检查项
        coordination_plan["safety_checks"] = [
            "检查电池电量和状态",
            "验证GPS信号强度",
            "确认飞行区域无障碍物",
            "检查云台和相机功能",
            "验证航线参数设置"
        ]
        
        # 生成应急预案
        coordination_plan["contingency_plans"] = [
            {
                "scenario": "电池电量不足",
                "action": "立即返航并更换电池"
            },
            {
                "scenario": "GPS信号丢失",
                "action": "切换到姿态模式并手动控制返航"
            },
            {
                "scenario": "恶劣天气",
                "action": "暂停任务并安全降落"
            }
        ]
        
        return coordination_plan
    
    def _calculate_overall_statistics(
        self,
        flight_configs: List[FlightConfiguration],
        coordination_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算总体统计信息。"""
        total_waypoints = sum(len(config.flight_path.waypoints) for config in flight_configs)
        total_photos = sum(config.photo_count for config in flight_configs)
        total_coverage = sum(config.coverage_area for config in flight_configs)
        total_distance = sum(
            sum(
                self.geometry_calc.haversine_distance(
                    config.flight_path.waypoints[i].coordinates,
                    config.flight_path.waypoints[i + 1].coordinates
                )
                for i in range(len(config.flight_path.waypoints) - 1)
            )
            for config in flight_configs
        )
        
        return {
            "total_flights": len(flight_configs),
            "total_waypoints": total_waypoints,
            "total_photos": total_photos,
            "total_coverage_hectares": round(total_coverage, 2),
            "total_distance_km": round(total_distance / 1000, 2),
            "total_execution_time_minutes": coordination_plan["total_execution_time"],
            "batteries_required": len(coordination_plan["flight_batches"]),
            "average_flight_duration": round(
                sum(config.estimated_duration for config in flight_configs) / len(flight_configs), 2
            ),
            "efficiency_score": self._calculate_efficiency_score(flight_configs, coordination_plan)
        }
    
    def _calculate_efficiency_score(
        self,
        flight_configs: List[FlightConfiguration],
        coordination_plan: Dict[str, Any]
    ) -> float:
        """计算效率分数。"""
        # 基于多个因素计算效率分数
        total_flight_time = sum(config.estimated_duration for config in flight_configs)
        total_execution_time = coordination_plan["total_execution_time"]
        
        # 时间效率
        time_efficiency = total_flight_time / total_execution_time if total_execution_time > 0 else 0
        
        # 电池效率
        battery_count = len(coordination_plan["flight_batches"])
        battery_efficiency = 1.0 / battery_count if battery_count > 0 else 0
        
        # 综合效率分数
        efficiency_score = (time_efficiency * 0.6 + battery_efficiency * 0.4) * 100
        
        return round(min(efficiency_score, 100.0), 1)
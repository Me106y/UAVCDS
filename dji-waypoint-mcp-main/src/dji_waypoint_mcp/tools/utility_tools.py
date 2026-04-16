"""
辅助工具集。
包含坐标转换、距离计算、航线统计等实用功能。
"""

import math
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
from datetime import datetime

from mcp.types import Tool
from pydantic import BaseModel, Field, ValidationError

from .base import BaseTool, ValidationMixin
from ..models import Coordinates, Waypoint, FlightPath
from ..utils.geometry import geometry_calculator
from ..utils.coordinate_transforms import coordinate_transformer
from ..config import settings


class CoordinateSystem(str, Enum):
    """坐标系统。"""
    WGS84 = "WGS84"
    GCJ02 = "GCJ02"
    BD09 = "BD09"
    UTM = "UTM"
    MERCATOR = "MERCATOR"


class DistanceUnit(str, Enum):
    """距离单位。"""
    METERS = "meters"
    KILOMETERS = "kilometers"
    FEET = "feet"
    MILES = "miles"
    NAUTICAL_MILES = "nautical_miles"


class CoordinateConversionInput(BaseModel):
    """坐标转换输入参数。"""
    coordinates: List[Dict[str, float]] = Field(..., min_items=1, description="坐标列表")
    source_system: CoordinateSystem = Field(..., description="源坐标系")
    target_system: CoordinateSystem = Field(..., description="目标坐标系")
    utm_zone: Optional[int] = Field(None, ge=1, le=60, description="UTM区域号")
    utm_hemisphere: Optional[str] = Field(None, description="UTM半球(N/S)")


class DistanceCalculationInput(BaseModel):
    """距离计算输入参数。"""
    points: List[Dict[str, float]] = Field(..., min_items=2, description="坐标点列表")
    unit: DistanceUnit = Field(default=DistanceUnit.METERS, description="距离单位")
    calculation_method: str = Field(default="haversine", description="计算方法")
    include_altitude: bool = Field(default=False, description="是否包含高度差")


class FlightPlanAnalysisInput(BaseModel):
    """航线分析输入参数。"""
    waypoints: List[Dict[str, Any]] = Field(..., min_items=2, description="航点列表")
    flight_speed: float = Field(default=5.0, ge=1, le=20, description="飞行速度(m/s)")
    include_detailed_stats: bool = Field(default=False, description="包含详细统计")
    analyze_efficiency: bool = Field(default=False, description="分析效率")


class UtilityTools(BaseTool, ValidationMixin):
    """辅助工具集合。"""
    
    def __init__(self):
        """初始化辅助工具。"""
        super().__init__()
        self.geometry_calc = geometry_calculator
        self.coord_transformer = coordinate_transformer
    
    def get_tool_definition(self) -> Tool:
        """获取MCP工具定义。"""
        return Tool(
            name="utility_functions",
            description="提供坐标转换、距离计算、航线分析等辅助功能",
            inputSchema={
                "type": "object",
                "properties": {
                    "function_type": {
                        "type": "string",
                        "enum": ["convert_coordinates", "calculate_distance", "analyze_flight_plan", "validate_coordinates"],
                        "description": "功能类型"
                    },
                    "coordinates": {
                        "type": "array",
                        "description": "坐标列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "latitude": {"type": "number", "minimum": -90, "maximum": 90},
                                "longitude": {"type": "number", "minimum": -180, "maximum": 180},
                                "altitude": {"type": "number", "minimum": -1000, "maximum": 10000}
                            },
                            "required": ["latitude", "longitude"]
                        }
                    },
                    "source_system": {
                        "type": "string",
                        "enum": ["WGS84", "GCJ02", "BD09", "UTM", "MERCATOR"],
                        "description": "源坐标系"
                    },
                    "target_system": {
                        "type": "string",
                        "enum": ["WGS84", "GCJ02", "BD09", "UTM", "MERCATOR"],
                        "description": "目标坐标系"
                    },
                    "points": {
                        "type": "array",
                        "description": "计算距离的点列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "latitude": {"type": "number"},
                                "longitude": {"type": "number"},
                                "altitude": {"type": "number"}
                            },
                            "required": ["latitude", "longitude"]
                        }
                    },
                    "waypoints": {
                        "type": "array",
                        "description": "航点列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "index": {"type": "integer"},
                                "coordinates": {
                                    "type": "object",
                                    "properties": {
                                        "latitude": {"type": "number"},
                                        "longitude": {"type": "number"},
                                        "altitude": {"type": "number"}
                                    },
                                    "required": ["latitude", "longitude", "altitude"]
                                },
                                "speed": {"type": "number", "minimum": 1, "maximum": 20},
                                "actions": {"type": "array"}
                            },
                            "required": ["coordinates"]
                        }
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["meters", "kilometers", "feet", "miles", "nautical_miles"],
                        "default": "meters",
                        "description": "距离单位"
                    },
                    "calculation_method": {
                        "type": "string",
                        "enum": ["haversine", "vincenty", "euclidean"],
                        "default": "haversine",
                        "description": "距离计算方法"
                    },
                    "flight_speed": {
                        "type": "number",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 5.0,
                        "description": "飞行速度(m/s)"
                    },
                    "include_altitude": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否包含高度差"
                    },
                    "include_detailed_stats": {
                        "type": "boolean",
                        "default": False,
                        "description": "包含详细统计"
                    },
                    "analyze_efficiency": {
                        "type": "boolean",
                        "default": False,
                        "description": "分析航线效率"
                    },
                    "utm_zone": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 60,
                        "description": "UTM区域号"
                    },
                    "utm_hemisphere": {
                        "type": "string",
                        "enum": ["N", "S"],
                        "description": "UTM半球"
                    }
                },
                "required": ["function_type"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行辅助功能。"""
        try:
            function_type = arguments.get("function_type")
            
            self.logger.info(f"执行辅助功能: {function_type}")
            
            if function_type == "convert_coordinates":
                result = await self._convert_coordinates(arguments)
            elif function_type == "calculate_distance":
                result = await self._calculate_distance(arguments)
            elif function_type == "analyze_flight_plan":
                result = await self._analyze_flight_plan(arguments)
            elif function_type == "validate_coordinates":
                result = await self._validate_coordinates(arguments)
            else:
                raise ValueError(f"不支持的功能类型: {function_type}")
            
            return self.format_success_response(
                f"辅助功能执行完成: {function_type}",
                result
            )
            
        except ValidationError as e:
            self.logger.error(f"辅助工具验证错误: {e}")
            return self.format_error_response(f"输入参数无效: {e}")
        
        except ValueError as e:
            self.logger.error(f"辅助工具值错误: {e}")
            return self.format_error_response(str(e))
        
        except Exception as e:
            self.logger.error(f"辅助工具意外错误: {e}", exc_info=True)
            return self.format_error_response(f"辅助功能执行失败: {e}")
    
    async def _convert_coordinates(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """坐标转换功能。"""
        coordinates = arguments.get("coordinates", [])
        source_system = arguments.get("source_system", "WGS84")
        target_system = arguments.get("target_system", "WGS84")
        utm_zone = arguments.get("utm_zone")
        utm_hemisphere = arguments.get("utm_hemisphere", "N")
        
        if not coordinates:
            raise ValueError("需要提供坐标数据")
        
        converted_coordinates = []
        conversion_info = {
            "source_system": source_system,
            "target_system": target_system,
            "total_points": len(coordinates),
            "conversion_method": "direct",
            "accuracy_note": "转换精度取决于源数据质量"
        }
        
        for i, coord in enumerate(coordinates):
            try:
                lat = coord["latitude"]
                lon = coord["longitude"]
                alt = coord.get("altitude", 0.0)
                
                # 执行坐标转换
                if source_system == target_system:
                    # 相同坐标系，直接返回
                    converted_lat, converted_lon = lat, lon
                elif source_system == "WGS84" and target_system == "GCJ02":
                    converted_lat, converted_lon = self.coord_transformer.wgs84_to_gcj02(lat, lon)
                elif source_system == "GCJ02" and target_system == "WGS84":
                    converted_lat, converted_lon = self.coord_transformer.gcj02_to_wgs84(lat, lon)
                elif source_system == "WGS84" and target_system == "BD09":
                    # WGS84 -> GCJ02 -> BD09
                    gcj_lat, gcj_lon = self.coord_transformer.wgs84_to_gcj02(lat, lon)
                    converted_lat, converted_lon = self.coord_transformer.gcj02_to_bd09(gcj_lat, gcj_lon)
                elif source_system == "BD09" and target_system == "WGS84":
                    # BD09 -> GCJ02 -> WGS84
                    gcj_lat, gcj_lon = self.coord_transformer.bd09_to_gcj02(lat, lon)
                    converted_lat, converted_lon = self.coord_transformer.gcj02_to_wgs84(gcj_lat, gcj_lon)
                elif target_system == "UTM":
                    if not utm_zone:
                        # 自动计算UTM区域
                        utm_zone = int((lon + 180) / 6) + 1
                    converted_lat, converted_lon = self._convert_to_utm(lat, lon, utm_zone, utm_hemisphere)
                    conversion_info["utm_zone"] = utm_zone
                    conversion_info["utm_hemisphere"] = utm_hemisphere
                else:
                    # 其他转换组合
                    converted_lat, converted_lon = self._generic_coordinate_conversion(
                        lat, lon, source_system, target_system
                    )
                
                converted_coord = {
                    "original_index": i,
                    "original": {"latitude": lat, "longitude": lon, "altitude": alt},
                    "converted": {
                        "latitude": round(converted_lat, 8),
                        "longitude": round(converted_lon, 8),
                        "altitude": alt
                    }
                }
                
                # 计算转换偏差
                if source_system != target_system:
                    offset_distance = self.geometry_calc.haversine_distance(
                        Coordinates(latitude=lat, longitude=lon),
                        Coordinates(latitude=converted_lat, longitude=converted_lon)
                    )
                    converted_coord["offset_distance_meters"] = round(offset_distance, 2)
                
                converted_coordinates.append(converted_coord)
                
            except Exception as e:
                self.logger.warning(f"转换坐标 {i} 时出错: {e}")
                converted_coordinates.append({
                    "original_index": i,
                    "error": str(e),
                    "original": coord
                })
        
        return {
            "conversion_info": conversion_info,
            "converted_coordinates": converted_coordinates,
            "summary": {
                "successful_conversions": len([c for c in converted_coordinates if "error" not in c]),
                "failed_conversions": len([c for c in converted_coordinates if "error" in c]),
                "average_offset": self._calculate_average_offset(converted_coordinates)
            }
        }
    
    async def _calculate_distance(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """距离计算功能。"""
        points = arguments.get("points", [])
        unit = arguments.get("unit", "meters")
        calculation_method = arguments.get("calculation_method", "haversine")
        include_altitude = arguments.get("include_altitude", False)
        
        if len(points) < 2:
            raise ValueError("至少需要2个点来计算距离")
        
        distances = []
        total_distance = 0.0
        
        for i in range(len(points) - 1):
            point1 = points[i]
            point2 = points[i + 1]
            
            lat1, lon1 = point1["latitude"], point1["longitude"]
            lat2, lon2 = point2["latitude"], point2["longitude"]
            alt1 = point1.get("altitude", 0.0)
            alt2 = point2.get("altitude", 0.0)
            
            # 计算水平距离
            if calculation_method == "haversine":
                horizontal_distance = self.geometry_calc.haversine_distance(
                    Coordinates(latitude=lat1, longitude=lon1),
                    Coordinates(latitude=lat2, longitude=lon2)
                )
            elif calculation_method == "vincenty":
                horizontal_distance = self._vincenty_distance(lat1, lon1, lat2, lon2)
            elif calculation_method == "euclidean":
                horizontal_distance = self._euclidean_distance(lat1, lon1, lat2, lon2)
            else:
                horizontal_distance = self.geometry_calc.haversine_distance(
                    Coordinates(latitude=lat1, longitude=lon1),
                    Coordinates(latitude=lat2, longitude=lon2)
                )
            
            # 计算3D距离（如果包含高度）
            if include_altitude:
                altitude_diff = abs(alt2 - alt1)
                total_3d_distance = math.sqrt(horizontal_distance**2 + altitude_diff**2)
            else:
                total_3d_distance = horizontal_distance
            
            # 转换单位
            distance_in_unit = self._convert_distance_unit(total_3d_distance, "meters", unit)
            horizontal_in_unit = self._convert_distance_unit(horizontal_distance, "meters", unit)
            
            segment_info = {
                "segment": i + 1,
                "from_point": {"latitude": lat1, "longitude": lon1, "altitude": alt1},
                "to_point": {"latitude": lat2, "longitude": lon2, "altitude": alt2},
                "horizontal_distance": round(horizontal_in_unit, 3),
                "total_distance": round(distance_in_unit, 3),
                "unit": unit
            }
            
            if include_altitude:
                segment_info["altitude_difference"] = round(alt2 - alt1, 2)
                segment_info["slope_angle"] = round(
                    math.degrees(math.atan2(abs(alt2 - alt1), horizontal_distance)), 2
                ) if horizontal_distance > 0 else 0.0
            
            distances.append(segment_info)
            total_distance += distance_in_unit
        
        # 计算统计信息
        segment_distances = [d["total_distance"] for d in distances]
        
        return {
            "calculation_info": {
                "method": calculation_method,
                "unit": unit,
                "include_altitude": include_altitude,
                "total_points": len(points),
                "total_segments": len(distances)
            },
            "distances": distances,
            "summary": {
                "total_distance": round(total_distance, 3),
                "average_segment_distance": round(sum(segment_distances) / len(segment_distances), 3),
                "min_segment_distance": round(min(segment_distances), 3),
                "max_segment_distance": round(max(segment_distances), 3),
                "unit": unit
            }
        }
    
    async def _analyze_flight_plan(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """航线分析功能。"""
        waypoints_data = arguments.get("waypoints", [])
        flight_speed = arguments.get("flight_speed", 5.0)
        include_detailed_stats = arguments.get("include_detailed_stats", False)
        analyze_efficiency = arguments.get("analyze_efficiency", False)
        
        if len(waypoints_data) < 2:
            raise ValueError("至少需要2个航点进行分析")
        
        # 解析航点
        waypoints = []
        for wp_data in waypoints_data:
            coords_data = wp_data["coordinates"]
            coordinates = Coordinates(
                latitude=coords_data["latitude"],
                longitude=coords_data["longitude"],
                altitude=coords_data["altitude"]
            )
            
            waypoint = Waypoint(
                index=wp_data.get("index", len(waypoints)),
                coordinates=coordinates,
                speed=wp_data.get("speed", flight_speed)
            )
            waypoints.append(waypoint)
        
        # 创建航线路径
        flight_path = FlightPath(waypoints=waypoints)
        
        # 基础统计
        total_distance = 0.0
        segment_distances = []
        altitude_changes = []
        speed_changes = []
        
        for i in range(len(waypoints) - 1):
            wp1 = waypoints[i]
            wp2 = waypoints[i + 1]
            
            # 计算距离
            distance = self.geometry_calc.haversine_distance(wp1.coordinates, wp2.coordinates)
            total_distance += distance
            segment_distances.append(distance)
            
            # 高度变化
            alt_change = wp2.coordinates.altitude - wp1.coordinates.altitude
            altitude_changes.append(alt_change)
            
            # 速度变化
            speed_changes.append(wp2.speed - wp1.speed)
        
        # 计算飞行时间
        total_time = total_distance / flight_speed
        
        # 基础分析结果
        analysis_result = {
            "basic_statistics": {
                "total_waypoints": len(waypoints),
                "total_distance_km": round(total_distance / 1000, 3),
                "total_distance_m": round(total_distance, 2),
                "estimated_flight_time_minutes": round(total_time / 60, 2),
                "estimated_flight_time_seconds": round(total_time, 1),
                "average_speed_ms": flight_speed,
                "average_segment_distance_m": round(sum(segment_distances) / len(segment_distances), 2)
            },
            "altitude_analysis": {
                "min_altitude": min(wp.coordinates.altitude for wp in waypoints),
                "max_altitude": max(wp.coordinates.altitude for wp in waypoints),
                "altitude_range": max(wp.coordinates.altitude for wp in waypoints) - min(wp.coordinates.altitude for wp in waypoints),
                "total_ascent": sum(change for change in altitude_changes if change > 0),
                "total_descent": abs(sum(change for change in altitude_changes if change < 0)),
                "average_altitude": sum(wp.coordinates.altitude for wp in waypoints) / len(waypoints)
            },
            "route_geometry": {
                "bounding_box": self._calculate_bounding_box(waypoints),
                "center_point": self._calculate_center_point(waypoints),
                "route_complexity": self._calculate_route_complexity(waypoints)
            }
        }
        
        # 详细统计
        if include_detailed_stats:
            analysis_result["detailed_statistics"] = {
                "segment_analysis": [
                    {
                        "segment": i + 1,
                        "distance_m": round(segment_distances[i], 2),
                        "altitude_change_m": round(altitude_changes[i], 2),
                        "estimated_time_s": round(segment_distances[i] / flight_speed, 1),
                        "bearing_degrees": self._calculate_bearing(waypoints[i], waypoints[i + 1])
                    }
                    for i in range(len(segment_distances))
                ],
                "waypoint_details": [
                    {
                        "index": wp.index,
                        "coordinates": {
                            "latitude": wp.coordinates.latitude,
                            "longitude": wp.coordinates.longitude,
                            "altitude": wp.coordinates.altitude
                        },
                        "speed": wp.speed,
                        "cumulative_distance": sum(segment_distances[:i]) if i > 0 else 0.0,
                        "estimated_arrival_time": sum(segment_distances[:i]) / flight_speed if i > 0 else 0.0
                    }
                    for i, wp in enumerate(waypoints)
                ]
            }
        
        # 效率分析
        if analyze_efficiency:
            analysis_result["efficiency_analysis"] = {
                "route_efficiency": self._calculate_route_efficiency(waypoints),
                "altitude_efficiency": self._calculate_altitude_efficiency(altitude_changes),
                "speed_optimization": self._analyze_speed_optimization(waypoints),
                "improvement_suggestions": self._generate_improvement_suggestions(waypoints, segment_distances)
            }
        
        return analysis_result
    
    async def _validate_coordinates(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """坐标验证功能。"""
        coordinates = arguments.get("coordinates", [])
        
        if not coordinates:
            raise ValueError("需要提供坐标数据")
        
        validation_results = []
        valid_count = 0
        
        for i, coord in enumerate(coordinates):
            result = {
                "index": i,
                "coordinate": coord,
                "is_valid": True,
                "issues": [],
                "warnings": []
            }
            
            lat = coord.get("latitude")
            lon = coord.get("longitude")
            alt = coord.get("altitude", 0.0)
            
            # 验证纬度
            if lat is None:
                result["is_valid"] = False
                result["issues"].append("缺少纬度值")
            elif not isinstance(lat, (int, float)):
                result["is_valid"] = False
                result["issues"].append("纬度必须是数值")
            elif not (-90 <= lat <= 90):
                result["is_valid"] = False
                result["issues"].append(f"纬度 {lat} 超出有效范围 [-90, 90]")
            elif abs(lat) < 0.0001:
                result["warnings"].append("纬度接近0，请确认坐标正确")
            
            # 验证经度
            if lon is None:
                result["is_valid"] = False
                result["issues"].append("缺少经度值")
            elif not isinstance(lon, (int, float)):
                result["is_valid"] = False
                result["issues"].append("经度必须是数值")
            elif not (-180 <= lon <= 180):
                result["is_valid"] = False
                result["issues"].append(f"经度 {lon} 超出有效范围 [-180, 180]")
            elif abs(lon) < 0.0001:
                result["warnings"].append("经度接近0，请确认坐标正确")
            
            # 验证高度
            if alt is not None:
                if not isinstance(alt, (int, float)):
                    result["warnings"].append("高度应该是数值")
                elif alt < -500:
                    result["warnings"].append(f"高度 {alt}m 过低，可能不合理")
                elif alt > 10000:
                    result["warnings"].append(f"高度 {alt}m 过高，可能不合理")
            
            # 检查坐标精度
            if lat is not None and lon is not None:
                lat_precision = len(str(lat).split('.')[-1]) if '.' in str(lat) else 0
                lon_precision = len(str(lon).split('.')[-1]) if '.' in str(lon) else 0
                
                if lat_precision < 5 or lon_precision < 5:
                    result["warnings"].append("坐标精度较低，可能影响定位准确性")
            
            if result["is_valid"]:
                valid_count += 1
            
            validation_results.append(result)
        
        return {
            "validation_summary": {
                "total_coordinates": len(coordinates),
                "valid_coordinates": valid_count,
                "invalid_coordinates": len(coordinates) - valid_count,
                "validation_rate": round(valid_count / len(coordinates) * 100, 2)
            },
            "validation_results": validation_results,
            "recommendations": self._generate_coordinate_recommendations(validation_results)
        }
    
    def _convert_to_utm(self, lat: float, lon: float, zone: int, hemisphere: str) -> Tuple[float, float]:
        """转换为UTM坐标（简化实现）。"""
        # 这是一个简化的UTM转换实现
        # 实际应用中应该使用专业的坐标转换库如pyproj
        
        # UTM转换的基本参数
        a = 6378137.0  # WGS84椭球长半轴
        f = 1/298.257223563  # WGS84扁率
        k0 = 0.9996  # UTM比例因子
        
        # 计算UTM坐标（简化算法）
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        
        # 中央经线
        lon0 = math.radians((zone - 1) * 6 - 180 + 3)
        
        # 简化的UTM投影计算
        x = k0 * a * (lon_rad - lon0) * math.cos(lat_rad)
        y = k0 * a * lat_rad
        
        # 添加UTM偏移
        x += 500000  # 东偏移
        if hemisphere == 'S':
            y += 10000000  # 南半球北偏移
        
        return y, x  # 返回北坐标, 东坐标
    
    def _generic_coordinate_conversion(
        self, 
        lat: float, 
        lon: float, 
        source: str, 
        target: str
    ) -> Tuple[float, float]:
        """通用坐标转换（简化实现）。"""
        # 这里实现其他坐标系转换的简化版本
        # 实际应用中应该使用专业库
        
        if source == "MERCATOR" or target == "MERCATOR":
            # Web Mercator投影
            if target == "MERCATOR":
                x = lon * 20037508.34 / 180
                y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
                y = y * 20037508.34 / 180
                return y, x
            else:
                # 从Mercator转回WGS84
                lon = lat * 180 / 20037508.34
                lat = math.atan(math.exp(lon * math.pi / 180)) * 360 / math.pi - 90
                return lat, lon
        
        # 默认返回原坐标
        return lat, lon
    
    def _vincenty_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Vincenty距离计算（简化实现）。"""
        # 简化的Vincenty公式实现
        # 实际应用中应该使用完整的Vincenty算法
        
        # 转换为弧度
        lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
        lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
        
        # 使用Haversine公式作为简化实现
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return 6371000 * c  # 地球半径6371km
    
    def _euclidean_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """欧几里得距离计算。"""
        # 将度转换为米（粗略）
        lat_diff = (lat2 - lat1) * 111000
        lon_diff = (lon2 - lon1) * 111000 * math.cos(math.radians((lat1 + lat2) / 2))
        
        return math.sqrt(lat_diff**2 + lon_diff**2)
    
    def _convert_distance_unit(self, distance: float, from_unit: str, to_unit: str) -> float:
        """距离单位转换。"""
        # 先转换为米
        if from_unit == "kilometers":
            distance_meters = distance * 1000
        elif from_unit == "feet":
            distance_meters = distance * 0.3048
        elif from_unit == "miles":
            distance_meters = distance * 1609.344
        elif from_unit == "nautical_miles":
            distance_meters = distance * 1852
        else:  # meters
            distance_meters = distance
        
        # 再转换为目标单位
        if to_unit == "kilometers":
            return distance_meters / 1000
        elif to_unit == "feet":
            return distance_meters / 0.3048
        elif to_unit == "miles":
            return distance_meters / 1609.344
        elif to_unit == "nautical_miles":
            return distance_meters / 1852
        else:  # meters
            return distance_meters
    
    def _calculate_average_offset(self, converted_coordinates: List[Dict]) -> float:
        """计算平均偏移距离。"""
        offsets = [c.get("offset_distance_meters", 0) for c in converted_coordinates if "offset_distance_meters" in c]
        return round(sum(offsets) / len(offsets), 2) if offsets else 0.0
    
    def _calculate_bounding_box(self, waypoints: List[Waypoint]) -> Dict[str, float]:
        """计算边界框。"""
        lats = [wp.coordinates.latitude for wp in waypoints]
        lons = [wp.coordinates.longitude for wp in waypoints]
        
        return {
            "min_latitude": min(lats),
            "max_latitude": max(lats),
            "min_longitude": min(lons),
            "max_longitude": max(lons),
            "center_latitude": (min(lats) + max(lats)) / 2,
            "center_longitude": (min(lons) + max(lons)) / 2
        }
    
    def _calculate_center_point(self, waypoints: List[Waypoint]) -> Dict[str, float]:
        """计算中心点。"""
        avg_lat = sum(wp.coordinates.latitude for wp in waypoints) / len(waypoints)
        avg_lon = sum(wp.coordinates.longitude for wp in waypoints) / len(waypoints)
        avg_alt = sum(wp.coordinates.altitude for wp in waypoints) / len(waypoints)
        
        return {
            "latitude": round(avg_lat, 6),
            "longitude": round(avg_lon, 6),
            "altitude": round(avg_alt, 2)
        }
    
    def _calculate_route_complexity(self, waypoints: List[Waypoint]) -> float:
        """计算航线复杂度。"""
        if len(waypoints) < 3:
            return 0.0
        
        # 基于转向角度计算复杂度
        total_turn_angle = 0.0
        
        for i in range(1, len(waypoints) - 1):
            wp1 = waypoints[i - 1]
            wp2 = waypoints[i]
            wp3 = waypoints[i + 1]
            
            # 计算转向角
            bearing1 = self._calculate_bearing(wp1, wp2)
            bearing2 = self._calculate_bearing(wp2, wp3)
            
            turn_angle = abs(bearing2 - bearing1)
            if turn_angle > 180:
                turn_angle = 360 - turn_angle
            
            total_turn_angle += turn_angle
        
        # 归一化复杂度 (0-1)
        max_possible_turn = (len(waypoints) - 2) * 180
        complexity = total_turn_angle / max_possible_turn if max_possible_turn > 0 else 0
        
        return round(complexity, 3)
    
    def _calculate_bearing(self, wp1: Waypoint, wp2: Waypoint) -> float:
        """计算方位角。"""
        lat1 = math.radians(wp1.coordinates.latitude)
        lat2 = math.radians(wp2.coordinates.latitude)
        dlon = math.radians(wp2.coordinates.longitude - wp1.coordinates.longitude)
        
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return round(bearing, 2)
    
    def _calculate_route_efficiency(self, waypoints: List[Waypoint]) -> Dict[str, float]:
        """计算航线效率。"""
        if len(waypoints) < 2:
            return {"efficiency_score": 1.0}
        
        # 计算实际路径长度
        actual_distance = 0.0
        for i in range(len(waypoints) - 1):
            distance = self.geometry_calc.haversine_distance(
                waypoints[i].coordinates,
                waypoints[i + 1].coordinates
            )
            actual_distance += distance
        
        # 计算直线距离
        direct_distance = self.geometry_calc.haversine_distance(
            waypoints[0].coordinates,
            waypoints[-1].coordinates
        )
        
        # 效率分数 = 直线距离 / 实际距离
        efficiency_score = direct_distance / actual_distance if actual_distance > 0 else 1.0
        
        return {
            "efficiency_score": round(efficiency_score, 3),
            "actual_distance": round(actual_distance, 2),
            "direct_distance": round(direct_distance, 2),
            "detour_ratio": round(actual_distance / direct_distance, 2) if direct_distance > 0 else 1.0
        }
    
    def _calculate_altitude_efficiency(self, altitude_changes: List[float]) -> Dict[str, float]:
        """计算高度效率。"""
        if not altitude_changes:
            return {"altitude_efficiency": 1.0}
        
        total_change = sum(abs(change) for change in altitude_changes)
        net_change = abs(sum(altitude_changes))
        
        # 高度效率 = 净变化 / 总变化
        efficiency = net_change / total_change if total_change > 0 else 1.0
        
        return {
            "altitude_efficiency": round(efficiency, 3),
            "total_altitude_change": round(total_change, 2),
            "net_altitude_change": round(net_change, 2),
            "unnecessary_altitude_change": round(total_change - net_change, 2)
        }
    
    def _analyze_speed_optimization(self, waypoints: List[Waypoint]) -> Dict[str, Any]:
        """分析速度优化。"""
        speeds = [wp.speed for wp in waypoints]
        
        return {
            "average_speed": round(sum(speeds) / len(speeds), 2),
            "min_speed": min(speeds),
            "max_speed": max(speeds),
            "speed_variance": round(sum((s - sum(speeds)/len(speeds))**2 for s in speeds) / len(speeds), 2),
            "speed_optimization_potential": "low" if max(speeds) - min(speeds) < 2 else "medium" if max(speeds) - min(speeds) < 5 else "high"
        }
    
    def _generate_improvement_suggestions(
        self, 
        waypoints: List[Waypoint], 
        segment_distances: List[float]
    ) -> List[str]:
        """生成改进建议。"""
        suggestions = []
        
        # 检查短距离段
        short_segments = [i for i, d in enumerate(segment_distances) if d < 10]
        if short_segments:
            suggestions.append(f"发现 {len(short_segments)} 个短距离段(<10m)，考虑合并相邻航点")
        
        # 检查长距离段
        long_segments = [i for i, d in enumerate(segment_distances) if d > 1000]
        if long_segments:
            suggestions.append(f"发现 {len(long_segments)} 个长距离段(>1km)，考虑添加中间航点")
        
        # 检查高度变化
        altitude_changes = []
        for i in range(len(waypoints) - 1):
            alt_change = abs(waypoints[i + 1].coordinates.altitude - waypoints[i].coordinates.altitude)
            altitude_changes.append(alt_change)
        
        large_alt_changes = [i for i, c in enumerate(altitude_changes) if c > 50]
        if large_alt_changes:
            suggestions.append(f"发现 {len(large_alt_changes)} 个大高度变化段(>50m)，考虑渐进式高度调整")
        
        return suggestions
    
    def _generate_coordinate_recommendations(self, validation_results: List[Dict]) -> List[str]:
        """生成坐标建议。"""
        recommendations = []
        
        invalid_count = len([r for r in validation_results if not r["is_valid"]])
        warning_count = len([r for r in validation_results if r["warnings"]])
        
        if invalid_count > 0:
            recommendations.append(f"修复 {invalid_count} 个无效坐标")
        
        if warning_count > 0:
            recommendations.append(f"检查 {warning_count} 个有警告的坐标")
        
        # 检查精度问题
        low_precision_count = len([
            r for r in validation_results 
            if any("精度较低" in w for w in r.get("warnings", []))
        ])
        
        if low_precision_count > 0:
            recommendations.append("提高坐标精度以获得更准确的定位")
        
        return recommendations
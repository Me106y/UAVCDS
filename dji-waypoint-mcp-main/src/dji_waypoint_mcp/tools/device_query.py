"""
设备查询和兼容性检查工具。
"""

from typing import Any, Dict, List, Optional, Union
from enum import Enum

from mcp.types import Tool
from pydantic import BaseModel, Field, ValidationError

from .base import BaseTool, ValidationMixin
from ..data.aircraft_database import aircraft_database, AircraftSpecs, PayloadSpecs
from ..config import settings


class QueryType(str, Enum):
    """查询类型。"""
    AIRCRAFT_INFO = "aircraft_info"
    PAYLOAD_INFO = "payload_info"
    COMPATIBILITY = "compatibility"
    SEARCH = "search"
    CAPABILITIES = "capabilities"


class DeviceQueryInput(BaseModel):
    """设备查询输入参数。"""
    query_type: QueryType = Field(..., description="查询类型")
    aircraft_id: Optional[str] = Field(None, description="无人机型号ID")
    payload_id: Optional[str] = Field(None, description="负载ID")
    search_criteria: Optional[Dict[str, Any]] = Field(None, description="搜索条件")
    include_details: bool = Field(default=False, description="包含详细信息")


class DeviceQueryTool(BaseTool, ValidationMixin):
    """设备查询工具。"""
    
    def __init__(self):
        """初始化设备查询工具。"""
        super().__init__()
        self.database = aircraft_database
    
    def get_tool_definition(self) -> Tool:
        """获取MCP工具定义。"""
        return Tool(
            name="query_device_info",
            description="查询无人机设备信息、负载规格和兼容性",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["aircraft_info", "payload_info", "compatibility", "search", "capabilities"],
                        "description": "查询类型"
                    },
                    "aircraft_id": {
                        "type": "string",
                        "description": "无人机型号ID (如: M300_RTK, M30, M3E)",
                        "enum": ["M300_RTK", "M350_RTK", "M30", "M30T", "M3E", "M3T", "M3M", "M3D", "M3TD"]
                    },
                    "payload_id": {
                        "type": "string",
                        "description": "负载ID (如: H20, H20T, P1)",
                        "enum": ["H20", "H20T", "P1", "L1", "L2"]
                    },
                    "search_criteria": {
                        "type": "object",
                        "description": "搜索条件",
                        "properties": {
                            "category": {
                                "type": "string",
                                "enum": ["consumer", "professional", "enterprise"],
                                "description": "设备类别"
                            },
                            "max_flight_time": {
                                "type": "number",
                                "minimum": 10,
                                "description": "最小飞行时间要求(分钟)"
                            },
                            "max_altitude": {
                                "type": "number",
                                "minimum": 100,
                                "description": "最小飞行高度要求(米)"
                            },
                            "rtk_positioning": {
                                "type": "boolean",
                                "description": "是否需要RTK定位"
                            },
                            "manufacturer": {
                                "type": "string",
                                "description": "制造商"
                            }
                        }
                    },
                    "include_details": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否包含详细技术规格"
                    }
                },
                "required": ["query_type"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行设备查询。"""
        try:
            # 验证输入参数
            query_input = DeviceQueryInput(**arguments)
            
            self.logger.info(f"执行设备查询: {query_input.query_type}")
            
            # 根据查询类型执行相应操作
            if query_input.query_type == QueryType.AIRCRAFT_INFO:
                result = self._query_aircraft_info(query_input)
            elif query_input.query_type == QueryType.PAYLOAD_INFO:
                result = self._query_payload_info(query_input)
            elif query_input.query_type == QueryType.COMPATIBILITY:
                result = self._query_compatibility(query_input)
            elif query_input.query_type == QueryType.SEARCH:
                result = self._search_devices(query_input)
            elif query_input.query_type == QueryType.CAPABILITIES:
                result = self._query_capabilities(query_input)
            else:
                raise ValueError(f"不支持的查询类型: {query_input.query_type}")
            
            return self.format_success_response(
                f"设备查询完成: {query_input.query_type}",
                result
            )
            
        except ValidationError as e:
            self.logger.error(f"设备查询验证错误: {e}")
            return self.format_error_response(f"输入参数无效: {e}")
        
        except ValueError as e:
            self.logger.error(f"设备查询值错误: {e}")
            return self.format_error_response(str(e))
        
        except Exception as e:
            self.logger.error(f"设备查询意外错误: {e}", exc_info=True)
            return self.format_error_response(f"设备查询失败: {e}")
    
    def _query_aircraft_info(self, query_input: DeviceQueryInput) -> Dict[str, Any]:
        """查询无人机信息。"""
        if not query_input.aircraft_id:
            # 返回所有无人机列表
            all_aircraft = self.database.get_all_aircraft()
            return {
                "aircraft_count": len(all_aircraft),
                "aircraft_list": [
                    {
                        "aircraft_id": specs.aircraft_id,
                        "model_name": specs.model_name,
                        "category": specs.category,
                        "manufacturer": specs.manufacturer,
                        "release_year": specs.release_year
                    }
                    for specs in all_aircraft
                ]
            }
        
        # 查询特定无人机
        aircraft_specs = self.database.get_aircraft_specs(query_input.aircraft_id)
        if not aircraft_specs:
            raise ValueError(f"未找到无人机: {query_input.aircraft_id}")
        
        result = {
            "aircraft_id": aircraft_specs.aircraft_id,
            "model_name": aircraft_specs.model_name,
            "manufacturer": aircraft_specs.manufacturer,
            "category": aircraft_specs.category,
            "release_year": aircraft_specs.release_year,
            "basic_specs": {
                "max_flight_time": aircraft_specs.flight_specs.max_flight_time,
                "max_altitude": aircraft_specs.flight_specs.max_altitude,
                "max_speed": aircraft_specs.flight_specs.max_speed,
                "transmission_range": aircraft_specs.transmission_range,
                "weight": aircraft_specs.physical_specs.weight,
                "protection_rating": aircraft_specs.physical_specs.protection_rating
            },
            "features": {
                "rtk_positioning": aircraft_specs.metadata.get("rtk_positioning", False),
                "obstacle_sensing": "Obstacle Sensing" in aircraft_specs.safety_features,
                "intelligent_features_count": len(aircraft_specs.intelligent_features),
                "supported_payloads_count": len(aircraft_specs.supported_payloads)
            }
        }
        
        # 包含详细信息
        if query_input.include_details:
            result["detailed_specs"] = {
                "flight_specs": {
                    "max_flight_time": aircraft_specs.flight_specs.max_flight_time,
                    "max_flight_distance": aircraft_specs.flight_specs.max_flight_distance,
                    "max_altitude": aircraft_specs.flight_specs.max_altitude,
                    "max_speed": aircraft_specs.flight_specs.max_speed,
                    "wind_resistance": aircraft_specs.flight_specs.wind_resistance,
                    "operating_temperature": aircraft_specs.flight_specs.operating_temperature,
                    "positioning_accuracy": aircraft_specs.flight_specs.positioning_accuracy
                },
                "battery_specs": {
                    "capacity": aircraft_specs.battery_specs.capacity,
                    "voltage": aircraft_specs.battery_specs.voltage,
                    "type": aircraft_specs.battery_specs.type,
                    "charging_time": aircraft_specs.battery_specs.charging_time,
                    "weight": aircraft_specs.battery_specs.weight
                },
                "physical_specs": {
                    "dimensions": aircraft_specs.physical_specs.dimensions,
                    "weight": aircraft_specs.physical_specs.weight,
                    "folded_dimensions": aircraft_specs.physical_specs.folded_dimensions,
                    "protection_rating": aircraft_specs.physical_specs.protection_rating
                },
                "flight_modes": aircraft_specs.flight_modes,
                "intelligent_features": aircraft_specs.intelligent_features,
                "safety_features": aircraft_specs.safety_features
            }
            
            # 集成相机信息
            if aircraft_specs.integrated_camera:
                result["detailed_specs"]["integrated_camera"] = {
                    "sensor_size": f"{aircraft_specs.integrated_camera.sensor_width}x{aircraft_specs.integrated_camera.sensor_height}mm",
                    "focal_length": aircraft_specs.integrated_camera.focal_length,
                    "image_resolution": f"{aircraft_specs.integrated_camera.image_width}x{aircraft_specs.integrated_camera.image_height}",
                    "video_resolution": aircraft_specs.integrated_camera.video_resolution,
                    "photo_formats": aircraft_specs.integrated_camera.photo_formats
                }
            
            # 支持的负载
            if aircraft_specs.supported_payloads:
                result["detailed_specs"]["supported_payloads"] = [
                    {
                        "payload_id": payload.payload_id,
                        "name": payload.name,
                        "type": payload.type,
                        "weight": payload.weight
                    }
                    for payload in aircraft_specs.supported_payloads
                ]
        
        return result
    
    def _query_payload_info(self, query_input: DeviceQueryInput) -> Dict[str, Any]:
        """查询负载信息。"""
        if not query_input.payload_id:
            # 返回所有负载列表
            all_payloads = self.database.get_all_payloads()
            return {
                "payload_count": len(all_payloads),
                "payload_list": [
                    {
                        "payload_id": specs.payload_id,
                        "name": specs.name,
                        "type": specs.type,
                        "weight": specs.weight,
                        "mount_position": specs.mount_position
                    }
                    for specs in all_payloads
                ]
            }
        
        # 查询特定负载
        payload_specs = self.database.get_payload_specs(query_input.payload_id)
        if not payload_specs:
            raise ValueError(f"未找到负载: {query_input.payload_id}")
        
        result = {
            "payload_id": payload_specs.payload_id,
            "name": payload_specs.name,
            "type": payload_specs.type,
            "weight": payload_specs.weight,
            "power_consumption": payload_specs.power_consumption,
            "mount_position": payload_specs.mount_position
        }
        
        # 包含详细信息
        if query_input.include_details:
            result["detailed_specs"] = {}
            
            # 相机规格
            if payload_specs.camera_specs:
                result["detailed_specs"]["camera_specs"] = {
                    "sensor_size": f"{payload_specs.camera_specs.sensor_width}x{payload_specs.camera_specs.sensor_height}mm",
                    "focal_length": payload_specs.camera_specs.focal_length,
                    "image_resolution": f"{payload_specs.camera_specs.image_width}x{payload_specs.camera_specs.image_height}",
                    "pixel_size": payload_specs.camera_specs.pixel_size,
                    "iso_range": payload_specs.camera_specs.iso_range,
                    "video_resolution": payload_specs.camera_specs.video_resolution,
                    "photo_formats": payload_specs.camera_specs.photo_formats
                }
            
            # 云台规格
            if payload_specs.gimbal_specs:
                result["detailed_specs"]["gimbal_specs"] = {
                    "pitch_range": payload_specs.gimbal_specs.pitch_range,
                    "yaw_range": payload_specs.gimbal_specs.yaw_range,
                    "roll_range": payload_specs.gimbal_specs.roll_range,
                    "stabilization_modes": payload_specs.gimbal_specs.stabilization_modes
                }
            
            # 附加规格
            if payload_specs.additional_specs:
                result["detailed_specs"]["additional_specs"] = payload_specs.additional_specs
        
        return result
    
    def _query_compatibility(self, query_input: DeviceQueryInput) -> Dict[str, Any]:
        """查询兼容性。"""
        if not query_input.aircraft_id:
            raise ValueError("兼容性查询需要指定无人机型号")
        
        aircraft_specs = self.database.get_aircraft_specs(query_input.aircraft_id)
        if not aircraft_specs:
            raise ValueError(f"未找到无人机: {query_input.aircraft_id}")
        
        # 获取兼容的负载
        compatible_payloads = self.database.get_compatible_payloads(query_input.aircraft_id)
        
        result = {
            "aircraft_id": query_input.aircraft_id,
            "model_name": aircraft_specs.model_name,
            "compatible_payloads": [
                {
                    "payload_id": payload.payload_id,
                    "name": payload.name,
                    "type": payload.type,
                    "weight": payload.weight,
                    "compatibility_score": self._calculate_compatibility_score(aircraft_specs, payload)
                }
                for payload in compatible_payloads
            ],
            "compatibility_summary": {
                "total_compatible_payloads": len(compatible_payloads),
                "payload_types": list(set(payload.type for payload in compatible_payloads)),
                "weight_range": {
                    "min": min(payload.weight for payload in compatible_payloads) if compatible_payloads else 0,
                    "max": max(payload.weight for payload in compatible_payloads) if compatible_payloads else 0
                }
            }
        }
        
        # 如果指定了特定负载，检查具体兼容性
        if query_input.payload_id:
            payload_specs = self.database.get_payload_specs(query_input.payload_id)
            if payload_specs:
                is_compatible = payload_specs in compatible_payloads
                compatibility_details = self._analyze_compatibility(aircraft_specs, payload_specs)
                
                result["specific_compatibility"] = {
                    "payload_id": query_input.payload_id,
                    "payload_name": payload_specs.name,
                    "is_compatible": is_compatible,
                    "compatibility_score": self._calculate_compatibility_score(aircraft_specs, payload_specs),
                    "compatibility_details": compatibility_details
                }
        
        return result
    
    def _search_devices(self, query_input: DeviceQueryInput) -> Dict[str, Any]:
        """搜索设备。"""
        if not query_input.search_criteria:
            raise ValueError("搜索需要指定搜索条件")
        
        # 搜索无人机
        matching_aircraft = self.database.search_aircraft(**query_input.search_criteria)
        
        result = {
            "search_criteria": query_input.search_criteria,
            "matching_aircraft": [
                {
                    "aircraft_id": specs.aircraft_id,
                    "model_name": specs.model_name,
                    "category": specs.category,
                    "manufacturer": specs.manufacturer,
                    "match_score": self._calculate_search_match_score(specs, query_input.search_criteria)
                }
                for specs in matching_aircraft
            ],
            "search_summary": {
                "total_matches": len(matching_aircraft),
                "categories": list(set(specs.category for specs in matching_aircraft)),
                "manufacturers": list(set(specs.manufacturer for specs in matching_aircraft))
            }
        }
        
        # 包含详细信息
        if query_input.include_details:
            result["detailed_matches"] = [
                {
                    "aircraft_id": specs.aircraft_id,
                    "model_name": specs.model_name,
                    "key_specs": {
                        "max_flight_time": specs.flight_specs.max_flight_time,
                        "max_altitude": specs.flight_specs.max_altitude,
                        "transmission_range": specs.transmission_range,
                        "rtk_positioning": specs.metadata.get("rtk_positioning", False)
                    }
                }
                for specs in matching_aircraft
            ]
        
        return result
    
    def _query_capabilities(self, query_input: DeviceQueryInput) -> Dict[str, Any]:
        """查询设备能力。"""
        if not query_input.aircraft_id:
            # 返回所有设备的能力摘要
            all_aircraft = self.database.get_all_aircraft()
            return {
                "capabilities_summary": [
                    self.database.get_aircraft_capabilities(specs.aircraft_id)
                    for specs in all_aircraft
                ]
            }
        
        # 查询特定设备能力
        capabilities = self.database.get_aircraft_capabilities(query_input.aircraft_id)
        if not capabilities:
            raise ValueError(f"未找到无人机: {query_input.aircraft_id}")
        
        # 添加更详细的能力分析
        aircraft_specs = self.database.get_aircraft_specs(query_input.aircraft_id)
        if aircraft_specs:
            capabilities["detailed_capabilities"] = {
                "flight_performance": {
                    "endurance_rating": self._rate_flight_endurance(aircraft_specs.flight_specs.max_flight_time),
                    "altitude_capability": self._rate_altitude_capability(aircraft_specs.flight_specs.max_altitude),
                    "speed_rating": self._rate_speed_capability(aircraft_specs.flight_specs.max_speed),
                    "weather_resistance": self._rate_weather_resistance(aircraft_specs.flight_specs.wind_resistance)
                },
                "imaging_capabilities": {
                    "has_integrated_camera": aircraft_specs.integrated_camera is not None,
                    "payload_flexibility": len(aircraft_specs.supported_payloads),
                    "gimbal_capability": aircraft_specs.integrated_gimbal is not None
                },
                "operational_capabilities": {
                    "autonomous_features": len(aircraft_specs.intelligent_features),
                    "safety_systems": len(aircraft_specs.safety_features),
                    "professional_grade": aircraft_specs.category in ["professional", "enterprise"]
                }
            }
        
        return capabilities
    
    def _calculate_compatibility_score(self, aircraft_specs: AircraftSpecs, payload_specs: PayloadSpecs) -> float:
        """计算兼容性分数。"""
        score = 1.0
        
        # 检查重量兼容性
        if aircraft_specs.physical_specs.max_takeoff_weight:
            weight_ratio = payload_specs.weight / aircraft_specs.physical_specs.max_takeoff_weight
            if weight_ratio > 0.3:  # 负载超过30%最大起飞重量
                score -= 0.2
        
        # 检查功耗兼容性
        if payload_specs.power_consumption > 20:  # 高功耗设备
            score -= 0.1
        
        # 检查挂载位置兼容性
        if payload_specs.mount_position == "gimbal" and not aircraft_specs.integrated_gimbal:
            score -= 0.3
        
        return max(score, 0.0)
    
    def _analyze_compatibility(self, aircraft_specs: AircraftSpecs, payload_specs: PayloadSpecs) -> Dict[str, Any]:
        """分析详细兼容性。"""
        analysis = {
            "weight_compatibility": "good",
            "power_compatibility": "good",
            "mount_compatibility": "good",
            "issues": [],
            "recommendations": []
        }
        
        # 重量分析
        if aircraft_specs.physical_specs.max_takeoff_weight:
            weight_ratio = payload_specs.weight / aircraft_specs.physical_specs.max_takeoff_weight
            if weight_ratio > 0.3:
                analysis["weight_compatibility"] = "warning"
                analysis["issues"].append(f"负载重量占最大起飞重量的{weight_ratio:.1%}")
                analysis["recommendations"].append("考虑使用更轻的负载或减少其他载荷")
        
        # 功耗分析
        if payload_specs.power_consumption > 20:
            analysis["power_compatibility"] = "warning"
            analysis["issues"].append(f"负载功耗较高: {payload_specs.power_consumption}W")
            analysis["recommendations"].append("注意电池续航时间可能会缩短")
        
        # 挂载分析
        if payload_specs.mount_position == "gimbal" and not aircraft_specs.integrated_gimbal:
            analysis["mount_compatibility"] = "error"
            analysis["issues"].append("需要云台但无人机不支持")
            analysis["recommendations"].append("选择支持云台的无人机型号")
        
        return analysis
    
    def _calculate_search_match_score(self, aircraft_specs: AircraftSpecs, criteria: Dict[str, Any]) -> float:
        """计算搜索匹配分数。"""
        score = 1.0
        total_criteria = len(criteria)
        
        for key, value in criteria.items():
            if key == "max_flight_time":
                if aircraft_specs.flight_specs.max_flight_time >= value:
                    score += 0.2
            elif key == "max_altitude":
                if aircraft_specs.flight_specs.max_altitude >= value:
                    score += 0.2
            elif key == "category":
                if aircraft_specs.category == value:
                    score += 0.3
            elif key == "rtk_positioning":
                if aircraft_specs.metadata.get("rtk_positioning") == value:
                    score += 0.2
            elif key == "manufacturer":
                if aircraft_specs.manufacturer == value:
                    score += 0.1
        
        return min(score, 2.0)  # 最大分数2.0
    
    def _rate_flight_endurance(self, flight_time: float) -> str:
        """评估飞行续航能力。"""
        if flight_time >= 45:
            return "excellent"
        elif flight_time >= 30:
            return "good"
        elif flight_time >= 20:
            return "fair"
        else:
            return "limited"
    
    def _rate_altitude_capability(self, max_altitude: float) -> str:
        """评估高度能力。"""
        if max_altitude >= 6000:
            return "excellent"
        elif max_altitude >= 3000:
            return "good"
        elif max_altitude >= 1000:
            return "fair"
        else:
            return "limited"
    
    def _rate_speed_capability(self, max_speed: float) -> str:
        """评估速度能力。"""
        if max_speed >= 20:
            return "excellent"
        elif max_speed >= 15:
            return "good"
        elif max_speed >= 10:
            return "fair"
        else:
            return "limited"
    
    def _rate_weather_resistance(self, wind_resistance: float) -> str:
        """评估抗风能力。"""
        if wind_resistance >= 15:
            return "excellent"
        elif wind_resistance >= 12:
            return "good"
        elif wind_resistance >= 8:
            return "fair"
        else:
            return "limited"
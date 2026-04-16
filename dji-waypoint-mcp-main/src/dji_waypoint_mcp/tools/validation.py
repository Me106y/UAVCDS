"""
验证和兼容性检查工具。
"""

from typing import Any, Dict, List, Optional
from enum import Enum

from mcp.types import Tool
from pydantic import BaseModel, Field, ValidationError

from .base import BaseTool, ValidationMixin
from ..utils.compatibility_checker import compatibility_checker, CompatibilityLevel
from ..models import FlightPath, Waypoint, Coordinates
from ..config import settings


class ValidationType(str, Enum):
    """验证类型。"""
    MISSION_COMPATIBILITY = "mission_compatibility"
    PARAMETER_VALIDATION = "parameter_validation"
    FLIGHT_PATH_SAFETY = "flight_path_safety"
    RECOMMENDATIONS = "recommendations"


class ValidationInput(BaseModel):
    """验证输入参数。"""
    validation_type: ValidationType = Field(..., description="验证类型")
    aircraft_id: str = Field(..., description="无人机型号ID")
    mission_config: Dict[str, Any] = Field(..., description="任务配置")
    flight_path: Optional[Dict[str, Any]] = Field(None, description="航线路径")
    payload_id: Optional[str] = Field(None, description="负载ID")
    environmental_conditions: Optional[Dict[str, Any]] = Field(None, description="环境条件")
    auto_fix: bool = Field(default=False, description="是否应用自动修复")


class ValidationTool(BaseTool, ValidationMixin):
    """验证和兼容性检查工具。"""
    
    def __init__(self):
        """初始化验证工具。"""
        super().__init__()
        self.checker = compatibility_checker
    
    def get_tool_definition(self) -> Tool:
        """获取MCP工具定义。"""
        return Tool(
            name="validate_mission_compatibility",
            description="验证任务兼容性、检查参数范围和安全性",
            inputSchema={
                "type": "object",
                "properties": {
                    "validation_type": {
                        "type": "string",
                        "enum": ["mission_compatibility", "parameter_validation", "flight_path_safety", "recommendations"],
                        "description": "验证类型"
                    },
                    "aircraft_id": {
                        "type": "string",
                        "description": "无人机型号ID",
                        "enum": ["M300_RTK", "M350_RTK", "M30", "M30T", "M3E", "M3T", "M3M", "M3D", "M3TD"]
                    },
                    "mission_config": {
                        "type": "object",
                        "description": "任务配置参数",
                        "properties": {
                            "flight_height": {"type": "number", "minimum": 5, "maximum": 1000},
                            "flight_speed": {"type": "number", "minimum": 1, "maximum": 20},
                            "overlap_rate": {"type": "number", "minimum": 50, "maximum": 95},
                            "sidelap_rate": {"type": "number", "minimum": 30, "maximum": 90},
                            "gimbal_pitch": {"type": "number", "minimum": -90, "maximum": 35},
                            "photo_interval": {"type": "number", "minimum": 0.5, "maximum": 30}
                        },
                        "required": ["flight_height", "flight_speed"]
                    },
                    "flight_path": {
                        "type": "object",
                        "description": "航线路径数据",
                        "properties": {
                            "waypoints": {
                                "type": "array",
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
                                        }
                                    },
                                    "required": ["index", "coordinates"]
                                }
                            }
                        }
                    },
                    "payload_id": {
                        "type": "string",
                        "description": "负载ID",
                        "enum": ["H20", "H20T", "P1", "L1", "L2"]
                    },
                    "environmental_conditions": {
                        "type": "object",
                        "description": "环境条件",
                        "properties": {
                            "wind_speed": {"type": "number", "minimum": 0, "maximum": 30},
                            "temperature": {"type": "number", "minimum": -40, "maximum": 60},
                            "precipitation": {"type": "boolean"},
                            "visibility": {"type": "number", "minimum": 0, "maximum": 10000}
                        }
                    },
                    "auto_fix": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否应用自动修复"
                    }
                },
                "required": ["validation_type", "aircraft_id", "mission_config"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行验证检查。"""
        try:
            # 验证输入参数
            validation_input = ValidationInput(**arguments)
            
            self.logger.info(f"执行验证检查: {validation_input.validation_type}")
            
            # 解析航线路径
            flight_path = None
            if validation_input.flight_path:
                flight_path = self._parse_flight_path(validation_input.flight_path)
            
            # 根据验证类型执行相应检查
            if validation_input.validation_type == ValidationType.MISSION_COMPATIBILITY:
                result = self._check_mission_compatibility(validation_input, flight_path)
            elif validation_input.validation_type == ValidationType.PARAMETER_VALIDATION:
                result = self._validate_parameters(validation_input)
            elif validation_input.validation_type == ValidationType.FLIGHT_PATH_SAFETY:
                result = self._check_flight_path_safety(validation_input, flight_path)
            elif validation_input.validation_type == ValidationType.RECOMMENDATIONS:
                result = self._get_recommendations(validation_input)
            else:
                raise ValueError(f"不支持的验证类型: {validation_input.validation_type}")
            
            return self.format_success_response(
                f"验证检查完成: {validation_input.validation_type}",
                result
            )
            
        except ValidationError as e:
            self.logger.error(f"验证检查参数错误: {e}")
            return self.format_error_response(f"输入参数无效: {e}")
        
        except ValueError as e:
            self.logger.error(f"验证检查值错误: {e}")
            return self.format_error_response(str(e))
        
        except Exception as e:
            self.logger.error(f"验证检查意外错误: {e}", exc_info=True)
            return self.format_error_response(f"验证检查失败: {e}")
    
    def _parse_flight_path(self, flight_path_data: Dict[str, Any]) -> FlightPath:
        """解析航线路径数据。"""
        waypoints = []
        
        for wp_data in flight_path_data.get("waypoints", []):
            coords_data = wp_data["coordinates"]
            coordinates = Coordinates(
                latitude=coords_data["latitude"],
                longitude=coords_data["longitude"],
                altitude=coords_data["altitude"]
            )
            
            waypoint = Waypoint(
                index=wp_data["index"],
                coordinates=coordinates
            )
            waypoints.append(waypoint)
        
        return FlightPath(waypoints=waypoints)
    
    def _check_mission_compatibility(
        self, 
        validation_input: ValidationInput, 
        flight_path: Optional[FlightPath]
    ) -> Dict[str, Any]:
        """检查任务兼容性。"""
        # 执行兼容性检查
        report = self.checker.check_mission_compatibility(
            aircraft_id=validation_input.aircraft_id,
            mission_config=validation_input.mission_config,
            flight_path=flight_path,
            payload_id=validation_input.payload_id,
            environmental_conditions=validation_input.environmental_conditions
        )
        
        # 格式化结果
        result = {
            "overall_compatibility": report.overall_compatibility.value,
            "compatibility_score": report.compatibility_score,
            "summary": {
                "total_issues": len(report.issues),
                "total_warnings": len(report.warnings),
                "critical_issues": len([i for i in report.issues if i.level == CompatibilityLevel.CRITICAL]),
                "error_issues": len([i for i in report.issues if i.level == CompatibilityLevel.ERROR])
            },
            "issues": [
                {
                    "category": issue.category.value,
                    "level": issue.level.value,
                    "title": issue.title,
                    "description": issue.description,
                    "affected_parameters": issue.affected_parameters,
                    "recommendations": issue.recommendations,
                    "auto_fix_available": issue.auto_fix_available
                }
                for issue in report.issues
            ],
            "warnings": [
                {
                    "category": warning.category.value,
                    "level": warning.level.value,
                    "title": warning.title,
                    "description": warning.description,
                    "recommendations": warning.recommendations
                }
                for warning in report.warnings
            ],
            "recommendations": report.recommendations,
            "performance_impact": report.performance_impact
        }
        
        # 应用自动修复
        if validation_input.auto_fix and report.auto_fixes:
            fixed_config = self.checker.apply_auto_fixes(
                validation_input.mission_config,
                report.auto_fixes
            )
            result["auto_fixes"] = {
                "available": True,
                "original_config": validation_input.mission_config,
                "fixed_config": fixed_config,
                "applied_fixes": report.auto_fixes
            }
        elif report.auto_fixes:
            result["auto_fixes"] = {
                "available": True,
                "suggested_fixes": report.auto_fixes,
                "note": "使用 auto_fix=true 参数应用这些修复"
            }
        
        return result
    
    def _validate_parameters(self, validation_input: ValidationInput) -> Dict[str, Any]:
        """验证参数范围。"""
        recommendations = self.checker.get_parameter_recommendations(validation_input.aircraft_id)
        
        validation_results = {}
        issues = []
        
        for param, value in validation_input.mission_config.items():
            if param in recommendations:
                param_rec = recommendations[param]
                validation_result = {
                    "parameter": param,
                    "value": value,
                    "unit": param_rec.get("unit", ""),
                    "valid": True,
                    "issues": []
                }
                
                # 检查范围
                if "min" in param_rec and value < param_rec["min"]:
                    validation_result["valid"] = False
                    validation_result["issues"].append(f"值 {value} 低于最小限制 {param_rec['min']}")
                    issues.append(f"{param}: 值过低")
                
                if "max" in param_rec and value > param_rec["max"]:
                    validation_result["valid"] = False
                    validation_result["issues"].append(f"值 {value} 超过最大限制 {param_rec['max']}")
                    issues.append(f"{param}: 值过高")
                
                # 检查建议值
                if "recommended" in param_rec:
                    if isinstance(param_rec["recommended"], (int, float)):
                        if abs(value - param_rec["recommended"]) > param_rec["recommended"] * 0.5:
                            validation_result["issues"].append(f"建议值为 {param_rec['recommended']}")
                    elif isinstance(param_rec["recommended"], tuple):
                        rec_min, rec_max = param_rec["recommended"]
                        if value < rec_min or value > rec_max:
                            validation_result["issues"].append(f"建议范围为 [{rec_min}, {rec_max}]")
                
                validation_results[param] = validation_result
        
        return {
            "parameter_validation": validation_results,
            "overall_valid": len(issues) == 0,
            "issues_summary": issues,
            "parameter_recommendations": recommendations
        }
    
    def _check_flight_path_safety(
        self, 
        validation_input: ValidationInput, 
        flight_path: Optional[FlightPath]
    ) -> Dict[str, Any]:
        """检查航线安全性。"""
        if not flight_path:
            return {"error": "需要提供航线路径数据"}
        
        safety_issues = []
        warnings = []
        
        # 检查航点数量
        waypoint_count = len(flight_path.waypoints)
        if waypoint_count < 2:
            safety_issues.append("航点数量不足，至少需要2个航点")
        elif waypoint_count > 99:
            safety_issues.append("航点数量过多，最多支持99个航点")
        
        # 检查航点间距和高度变化
        for i in range(len(flight_path.waypoints) - 1):
            wp1 = flight_path.waypoints[i]
            wp2 = flight_path.waypoints[i + 1]
            
            # 计算距离
            import math
            lat_diff = wp2.coordinates.latitude - wp1.coordinates.latitude
            lon_diff = wp2.coordinates.longitude - wp1.coordinates.longitude
            distance = math.sqrt(lat_diff**2 + lon_diff**2) * 111000  # 粗略转换
            
            if distance < 5:
                warnings.append(f"航点 {i} 和 {i+1} 间距过短: {distance:.1f}m")
            elif distance > 2000:
                warnings.append(f"航点 {i} 和 {i+1} 间距过长: {distance:.1f}m")
            
            # 检查高度变化
            alt_diff = abs(wp2.coordinates.altitude - wp1.coordinates.altitude)
            if alt_diff > 100:
                warnings.append(f"航点 {i} 和 {i+1} 高度变化过大: {alt_diff:.1f}m")
        
        # 检查飞行高度
        altitudes = [wp.coordinates.altitude for wp in flight_path.waypoints]
        min_alt = min(altitudes)
        max_alt = max(altitudes)
        
        if min_alt < 5:
            safety_issues.append(f"最低飞行高度过低: {min_alt}m")
        if max_alt > 500:
            warnings.append(f"最高飞行高度较高: {max_alt}m")
        
        return {
            "flight_path_safety": {
                "waypoint_count": waypoint_count,
                "altitude_range": {"min": min_alt, "max": max_alt},
                "safety_level": "safe" if not safety_issues else "unsafe",
                "issues": safety_issues,
                "warnings": warnings
            },
            "safety_score": max(0, 1.0 - len(safety_issues) * 0.3 - len(warnings) * 0.1)
        }
    
    def _get_recommendations(self, validation_input: ValidationInput) -> Dict[str, Any]:
        """获取参数建议。"""
        recommendations = self.checker.get_parameter_recommendations(validation_input.aircraft_id)
        
        # 基于当前配置生成具体建议
        specific_recommendations = []
        
        for param, value in validation_input.mission_config.items():
            if param in recommendations:
                param_rec = recommendations[param]
                
                if "recommended" in param_rec:
                    if isinstance(param_rec["recommended"], (int, float)):
                        if value != param_rec["recommended"]:
                            specific_recommendations.append(
                                f"{param}: 当前值 {value}，建议值 {param_rec['recommended']}"
                            )
                    elif isinstance(param_rec["recommended"], tuple):
                        rec_min, rec_max = param_rec["recommended"]
                        if value < rec_min or value > rec_max:
                            specific_recommendations.append(
                                f"{param}: 当前值 {value}，建议范围 [{rec_min}, {rec_max}]"
                            )
        
        return {
            "parameter_recommendations": recommendations,
            "specific_recommendations": specific_recommendations,
            "optimization_tips": [
                "适当降低飞行速度可以提高图像质量",
                "保持80%左右的重叠率可以确保良好的拼接效果",
                "预留20%电量作为安全余量",
                "避免在恶劣天气条件下飞行"
            ]
        }
"""
兼容性检查系统。
用于验证无人机配置、检测冲突并提供解决建议。
"""

import math
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field

from ..data.aircraft_database import aircraft_database, AircraftSpecs, PayloadSpecs
from ..models import FlightPath, Waypoint, MissionConfig


class CompatibilityLevel(str, Enum):
    """兼容性级别。"""
    COMPATIBLE = "compatible"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueCategory(str, Enum):
    """问题类别。"""
    FLIGHT_PARAMETERS = "flight_parameters"
    PAYLOAD_COMPATIBILITY = "payload_compatibility"
    BATTERY_LIFE = "battery_life"
    WEATHER_CONDITIONS = "weather_conditions"
    SAFETY_LIMITS = "safety_limits"
    PERFORMANCE = "performance"


@dataclass
class CompatibilityIssue:
    """兼容性问题。"""
    category: IssueCategory
    level: CompatibilityLevel
    title: str
    description: str
    affected_parameters: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    auto_fix_available: bool = False
    fix_parameters: Optional[Dict[str, Any]] = None


@dataclass
class CompatibilityReport:
    """兼容性报告。"""
    overall_compatibility: CompatibilityLevel
    compatibility_score: float  # 0.0 - 1.0
    issues: List[CompatibilityIssue] = field(default_factory=list)
    warnings: List[CompatibilityIssue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    auto_fixes: Dict[str, Any] = field(default_factory=dict)
    performance_impact: Dict[str, float] = field(default_factory=dict)


class CompatibilityChecker:
    """兼容性检查器。"""
    
    def __init__(self):
        """初始化兼容性检查器。"""
        self.database = aircraft_database
        
        # 定义参数限制
        self.parameter_limits = {
            "flight_height": {"min": 5, "max": 500, "recommended_max": 120},
            "flight_speed": {"min": 1, "max": 15, "recommended_max": 10},
            "waypoint_count": {"min": 2, "max": 99, "recommended_max": 50},
            "flight_distance": {"min": 0.1, "max": 50, "recommended_max": 20},
            "gimbal_pitch": {"min": -90, "max": 35, "recommended_range": (-90, 0)},
            "photo_interval": {"min": 0.5, "max": 30, "recommended_min": 1.0},
            "overlap_rate": {"min": 50, "max": 95, "recommended_range": (70, 85)},
            "sidelap_rate": {"min": 30, "max": 90, "recommended_range": (60, 80)}
        }
    
    def check_mission_compatibility(
        self,
        aircraft_id: str,
        mission_config: Dict[str, Any],
        flight_path: Optional[FlightPath] = None,
        payload_id: Optional[str] = None,
        environmental_conditions: Optional[Dict[str, Any]] = None
    ) -> CompatibilityReport:
        """检查任务兼容性。"""
        report = CompatibilityReport(
            overall_compatibility=CompatibilityLevel.COMPATIBLE,
            compatibility_score=1.0
        )
        
        # 获取无人机规格
        aircraft_specs = self.database.get_aircraft_specs(aircraft_id)
        if not aircraft_specs:
            report.issues.append(CompatibilityIssue(
                category=IssueCategory.FLIGHT_PARAMETERS,
                level=CompatibilityLevel.CRITICAL,
                title="未知无人机型号",
                description=f"无法找到无人机型号: {aircraft_id}",
                recommendations=["请检查无人机型号是否正确"]
            ))
            report.overall_compatibility = CompatibilityLevel.CRITICAL
            report.compatibility_score = 0.0
            return report
        
        # 检查各个方面的兼容性
        self._check_flight_parameters(aircraft_specs, mission_config, report)
        self._check_payload_compatibility(aircraft_specs, payload_id, report)
        self._check_battery_requirements(aircraft_specs, mission_config, flight_path, report)
        self._check_performance_limits(aircraft_specs, mission_config, flight_path, report)
        
        if environmental_conditions:
            self._check_environmental_compatibility(aircraft_specs, environmental_conditions, report)
        
        if flight_path:
            self._check_flight_path_safety(aircraft_specs, flight_path, report)
        
        # 计算总体兼容性
        self._calculate_overall_compatibility(report)
        
        # 生成建议和自动修复
        self._generate_recommendations(report)
        self._generate_auto_fixes(aircraft_specs, mission_config, report)
        
        return report
    
    def _check_flight_parameters(
        self,
        aircraft_specs: AircraftSpecs,
        mission_config: Dict[str, Any],
        report: CompatibilityReport
    ):
        """检查飞行参数兼容性。"""
        # 检查飞行高度
        flight_height = mission_config.get("flight_height", 100.0)
        if flight_height > aircraft_specs.flight_specs.max_altitude:
            report.issues.append(CompatibilityIssue(
                category=IssueCategory.FLIGHT_PARAMETERS,
                level=CompatibilityLevel.ERROR,
                title="飞行高度超限",
                description=f"飞行高度 {flight_height}m 超过最大限制 {aircraft_specs.flight_specs.max_altitude}m",
                affected_parameters=["flight_height"],
                recommendations=[f"将飞行高度降低至 {aircraft_specs.flight_specs.max_altitude}m 以下"],
                auto_fix_available=True,
                fix_parameters={"flight_height": min(flight_height, aircraft_specs.flight_specs.max_altitude * 0.9)}
            ))
        elif flight_height > self.parameter_limits["flight_height"]["recommended_max"]:
            report.warnings.append(CompatibilityIssue(
                category=IssueCategory.FLIGHT_PARAMETERS,
                level=CompatibilityLevel.WARNING,
                title="飞行高度较高",
                description=f"飞行高度 {flight_height}m 超过建议值 {self.parameter_limits['flight_height']['recommended_max']}m",
                affected_parameters=["flight_height"],
                recommendations=["考虑降低飞行高度以提高安全性和图像质量"]
            ))
        
        # 检查飞行速度
        flight_speed = mission_config.get("flight_speed", 5.0)
        if flight_speed > aircraft_specs.flight_specs.max_speed:
            report.issues.append(CompatibilityIssue(
                category=IssueCategory.FLIGHT_PARAMETERS,
                level=CompatibilityLevel.ERROR,
                title="飞行速度超限",
                description=f"飞行速度 {flight_speed}m/s 超过最大限制 {aircraft_specs.flight_specs.max_speed}m/s",
                affected_parameters=["flight_speed"],
                recommendations=[f"将飞行速度降低至 {aircraft_specs.flight_specs.max_speed}m/s 以下"],
                auto_fix_available=True,
                fix_parameters={"flight_speed": min(flight_speed, aircraft_specs.flight_specs.max_speed * 0.9)}
            ))
        
        # 检查云台角度
        gimbal_pitch = mission_config.get("gimbal_pitch", -90.0)
        if aircraft_specs.integrated_gimbal:
            pitch_min, pitch_max = aircraft_specs.integrated_gimbal.pitch_range
            if gimbal_pitch < pitch_min or gimbal_pitch > pitch_max:
                report.issues.append(CompatibilityIssue(
                    category=IssueCategory.FLIGHT_PARAMETERS,
                    level=CompatibilityLevel.ERROR,
                    title="云台角度超限",
                    description=f"云台俯仰角 {gimbal_pitch}° 超出范围 [{pitch_min}°, {pitch_max}°]",
                    affected_parameters=["gimbal_pitch"],
                    recommendations=[f"将云台角度调整至 [{pitch_min}°, {pitch_max}°] 范围内"],
                    auto_fix_available=True,
                    fix_parameters={"gimbal_pitch": max(pitch_min, min(gimbal_pitch, pitch_max))}
                ))
        
        # 检查重叠率
        overlap_rate = mission_config.get("overlap_rate", 80.0)
        if overlap_rate < self.parameter_limits["overlap_rate"]["min"]:
            report.warnings.append(CompatibilityIssue(
                category=IssueCategory.PERFORMANCE,
                level=CompatibilityLevel.WARNING,
                title="重叠率过低",
                description=f"重叠率 {overlap_rate}% 低于建议值 {self.parameter_limits['overlap_rate']['min']}%",
                affected_parameters=["overlap_rate"],
                recommendations=["提高重叠率以确保图像拼接质量"]
            ))
        elif overlap_rate > self.parameter_limits["overlap_rate"]["max"]:
            report.warnings.append(CompatibilityIssue(
                category=IssueCategory.PERFORMANCE,
                level=CompatibilityLevel.WARNING,
                title="重叠率过高",
                description=f"重叠率 {overlap_rate}% 高于建议值 {self.parameter_limits['overlap_rate']['max']}%",
                affected_parameters=["overlap_rate"],
                recommendations=["降低重叠率以提高飞行效率"]
            ))
    
    def _check_payload_compatibility(
        self,
        aircraft_specs: AircraftSpecs,
        payload_id: Optional[str],
        report: CompatibilityReport
    ):
        """检查负载兼容性。"""
        if not payload_id:
            return
        
        payload_specs = self.database.get_payload_specs(payload_id)
        if not payload_specs:
            report.issues.append(CompatibilityIssue(
                category=IssueCategory.PAYLOAD_COMPATIBILITY,
                level=CompatibilityLevel.ERROR,
                title="未知负载型号",
                description=f"无法找到负载型号: {payload_id}",
                recommendations=["请检查负载型号是否正确"]
            ))
            return
        
        # 检查负载是否在支持列表中
        supported_payloads = [p.payload_id for p in aircraft_specs.supported_payloads]
        if payload_id not in supported_payloads:
            report.issues.append(CompatibilityIssue(
                category=IssueCategory.PAYLOAD_COMPATIBILITY,
                level=CompatibilityLevel.ERROR,
                title="负载不兼容",
                description=f"负载 {payload_id} 不在支持列表中",
                recommendations=[f"选择支持的负载: {', '.join(supported_payloads)}"]
            ))
            return
        
        # 检查重量兼容性
        if aircraft_specs.physical_specs.max_takeoff_weight:
            weight_ratio = payload_specs.weight / aircraft_specs.physical_specs.max_takeoff_weight
            if weight_ratio > 0.4:  # 超过40%最大起飞重量
                report.warnings.append(CompatibilityIssue(
                    category=IssueCategory.PAYLOAD_COMPATIBILITY,
                    level=CompatibilityLevel.WARNING,
                    title="负载重量较大",
                    description=f"负载重量占最大起飞重量的 {weight_ratio:.1%}",
                    recommendations=["注意可能影响飞行性能和续航时间"]
                ))
        
        # 检查功耗兼容性
        if payload_specs.power_consumption > 25:  # 高功耗负载
            report.warnings.append(CompatibilityIssue(
                category=IssueCategory.PAYLOAD_COMPATIBILITY,
                level=CompatibilityLevel.WARNING,
                title="负载功耗较高",
                description=f"负载功耗 {payload_specs.power_consumption}W 较高",
                recommendations=["注意可能缩短飞行时间"]
            ))
    
    def _check_battery_requirements(
        self,
        aircraft_specs: AircraftSpecs,
        mission_config: Dict[str, Any],
        flight_path: Optional[FlightPath],
        report: CompatibilityReport
    ):
        """检查电池需求。"""
        # 估算飞行时间
        estimated_flight_time = self._estimate_flight_time(mission_config, flight_path)
        max_flight_time = aircraft_specs.flight_specs.max_flight_time
        
        # 考虑安全余量（20%）
        safe_flight_time = max_flight_time * 0.8
        
        if estimated_flight_time > max_flight_time:
            report.issues.append(CompatibilityIssue(
                category=IssueCategory.BATTERY_LIFE,
                level=CompatibilityLevel.ERROR,
                title="飞行时间超限",
                description=f"预计飞行时间 {estimated_flight_time:.1f}分钟 超过最大续航 {max_flight_time:.1f}分钟",
                recommendations=["缩短航线或分割为多个子任务"],
                auto_fix_available=True
            ))
        elif estimated_flight_time > safe_flight_time:
            report.warnings.append(CompatibilityIssue(
                category=IssueCategory.BATTERY_LIFE,
                level=CompatibilityLevel.WARNING,
                title="飞行时间接近极限",
                description=f"预计飞行时间 {estimated_flight_time:.1f}分钟 接近最大续航",
                recommendations=["建议预留20%电量作为安全余量"]
            ))
        
        # 计算电池消耗率
        battery_consumption_rate = estimated_flight_time / max_flight_time
        report.performance_impact["battery_usage"] = battery_consumption_rate
    
    def _check_performance_limits(
        self,
        aircraft_specs: AircraftSpecs,
        mission_config: Dict[str, Any],
        flight_path: Optional[FlightPath],
        report: CompatibilityReport
    ):
        """检查性能限制。"""
        # 检查航点数量
        if flight_path:
            waypoint_count = len(flight_path.waypoints)
            max_waypoints = self.parameter_limits["waypoint_count"]["max"]
            
            if waypoint_count > max_waypoints:
                report.issues.append(CompatibilityIssue(
                    category=IssueCategory.PERFORMANCE,
                    level=CompatibilityLevel.ERROR,
                    title="航点数量超限",
                    description=f"航点数量 {waypoint_count} 超过最大限制 {max_waypoints}",
                    recommendations=["减少航点数量或分割航线"],
                    auto_fix_available=True
                ))
            elif waypoint_count > self.parameter_limits["waypoint_count"]["recommended_max"]:
                report.warnings.append(CompatibilityIssue(
                    category=IssueCategory.PERFORMANCE,
                    level=CompatibilityLevel.WARNING,
                    title="航点数量较多",
                    description=f"航点数量 {waypoint_count} 超过建议值 {self.parameter_limits['waypoint_count']['recommended_max']}",
                    recommendations=["考虑优化航线以减少航点数量"]
                ))
        
        # 检查飞行距离
        total_distance = self._calculate_total_distance(flight_path) if flight_path else 0
        max_distance = aircraft_specs.flight_specs.max_flight_distance * 1000  # 转换为米
        
        if total_distance > max_distance:
            report.issues.append(CompatibilityIssue(
                category=IssueCategory.PERFORMANCE,
                level=CompatibilityLevel.ERROR,
                title="飞行距离超限",
                description=f"总飞行距离 {total_distance/1000:.1f}km 超过最大限制 {max_distance/1000:.1f}km",
                recommendations=["缩短航线或分割为多个子任务"]
            ))
    
    def _check_environmental_compatibility(
        self,
        aircraft_specs: AircraftSpecs,
        environmental_conditions: Dict[str, Any],
        report: CompatibilityReport
    ):
        """检查环境兼容性。"""
        # 检查风速
        wind_speed = environmental_conditions.get("wind_speed", 0)
        max_wind_resistance = aircraft_specs.flight_specs.wind_resistance
        
        if wind_speed > max_wind_resistance:
            report.issues.append(CompatibilityIssue(
                category=IssueCategory.WEATHER_CONDITIONS,
                level=CompatibilityLevel.CRITICAL,
                title="风速超限",
                description=f"风速 {wind_speed}m/s 超过抗风能力 {max_wind_resistance}m/s",
                recommendations=["等待风速降低后再执行任务"]
            ))
        elif wind_speed > max_wind_resistance * 0.7:
            report.warnings.append(CompatibilityIssue(
                category=IssueCategory.WEATHER_CONDITIONS,
                level=CompatibilityLevel.WARNING,
                title="风速较大",
                description=f"风速 {wind_speed}m/s 接近抗风极限",
                recommendations=["注意飞行安全，考虑降低飞行速度"]
            ))
        
        # 检查温度
        temperature = environmental_conditions.get("temperature")
        if temperature is not None:
            temp_min, temp_max = aircraft_specs.flight_specs.operating_temperature
            if temperature < temp_min or temperature > temp_max:
                report.issues.append(CompatibilityIssue(
                    category=IssueCategory.WEATHER_CONDITIONS,
                    level=CompatibilityLevel.ERROR,
                    title="温度超出工作范围",
                    description=f"环境温度 {temperature}°C 超出工作范围 [{temp_min}°C, {temp_max}°C]",
                    recommendations=["等待温度适宜时再执行任务"]
                ))
        
        # 检查降水
        precipitation = environmental_conditions.get("precipitation", False)
        if precipitation and not aircraft_specs.physical_specs.protection_rating:
            report.warnings.append(CompatibilityIssue(
                category=IssueCategory.WEATHER_CONDITIONS,
                level=CompatibilityLevel.WARNING,
                title="降水天气",
                description="当前有降水，无人机无防护等级",
                recommendations=["避免在降水天气飞行"]
            ))
    
    def _check_flight_path_safety(
        self,
        aircraft_specs: AircraftSpecs,
        flight_path: FlightPath,
        report: CompatibilityReport
    ):
        """检查航线安全性。"""
        if not flight_path.waypoints:
            return
        
        # 检查航点间距离
        for i in range(len(flight_path.waypoints) - 1):
            wp1 = flight_path.waypoints[i]
            wp2 = flight_path.waypoints[i + 1]
            
            # 计算水平距离
            lat_diff = wp2.coordinates.latitude - wp1.coordinates.latitude
            lon_diff = wp2.coordinates.longitude - wp1.coordinates.longitude
            distance = math.sqrt(lat_diff**2 + lon_diff**2) * 111000  # 粗略转换为米
            
            # 检查距离是否过短
            if distance < 5:  # 小于5米
                report.warnings.append(CompatibilityIssue(
                    category=IssueCategory.SAFETY_LIMITS,
                    level=CompatibilityLevel.WARNING,
                    title="航点间距过短",
                    description=f"航点 {i} 和 {i+1} 间距离过短: {distance:.1f}m",
                    recommendations=["增加航点间距或合并相近航点"]
                ))
            
            # 检查高度变化
            alt_diff = abs(wp2.coordinates.altitude - wp1.coordinates.altitude)
            if alt_diff > 50:  # 高度变化超过50米
                report.warnings.append(CompatibilityIssue(
                    category=IssueCategory.SAFETY_LIMITS,
                    level=CompatibilityLevel.WARNING,
                    title="高度变化过大",
                    description=f"航点 {i} 和 {i+1} 高度变化过大: {alt_diff:.1f}m",
                    recommendations=["减少单次高度变化或增加中间航点"]
                ))
        
        # 检查最低飞行高度
        min_altitude = min(wp.coordinates.altitude for wp in flight_path.waypoints)
        if min_altitude < 10:  # 低于10米
            report.warnings.append(CompatibilityIssue(
                category=IssueCategory.SAFETY_LIMITS,
                level=CompatibilityLevel.WARNING,
                title="飞行高度过低",
                description=f"最低飞行高度 {min_altitude}m 可能存在安全风险",
                recommendations=["提高飞行高度以确保安全"]
            ))
    
    def _estimate_flight_time(
        self,
        mission_config: Dict[str, Any],
        flight_path: Optional[FlightPath]
    ) -> float:
        """估算飞行时间（分钟）。"""
        if not flight_path:
            return 0.0
        
        total_distance = self._calculate_total_distance(flight_path)
        flight_speed = mission_config.get("flight_speed", 5.0)
        
        # 基础飞行时间
        flight_time = total_distance / flight_speed / 60  # 转换为分钟
        
        # 添加起降和悬停时间
        takeoff_landing_time = 2.0  # 2分钟
        hover_time = len(flight_path.waypoints) * 0.1  # 每个航点0.1分钟悬停
        
        return flight_time + takeoff_landing_time + hover_time
    
    def _calculate_total_distance(self, flight_path: FlightPath) -> float:
        """计算总飞行距离（米）。"""
        if len(flight_path.waypoints) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(len(flight_path.waypoints) - 1):
            wp1 = flight_path.waypoints[i]
            wp2 = flight_path.waypoints[i + 1]
            
            # 使用Haversine公式计算距离
            lat1, lon1 = math.radians(wp1.coordinates.latitude), math.radians(wp1.coordinates.longitude)
            lat2, lon2 = math.radians(wp2.coordinates.latitude), math.radians(wp2.coordinates.longitude)
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            distance = 6371000 * c  # 地球半径6371km
            
            total_distance += distance
        
        return total_distance
    
    def _calculate_overall_compatibility(self, report: CompatibilityReport):
        """计算总体兼容性。"""
        # 根据问题严重程度计算分数
        score = 1.0
        
        for issue in report.issues:
            if issue.level == CompatibilityLevel.CRITICAL:
                score -= 0.5
                report.overall_compatibility = CompatibilityLevel.CRITICAL
            elif issue.level == CompatibilityLevel.ERROR:
                score -= 0.3
                if report.overall_compatibility == CompatibilityLevel.COMPATIBLE:
                    report.overall_compatibility = CompatibilityLevel.ERROR
            elif issue.level == CompatibilityLevel.WARNING:
                score -= 0.1
                if report.overall_compatibility == CompatibilityLevel.COMPATIBLE:
                    report.overall_compatibility = CompatibilityLevel.WARNING
        
        for warning in report.warnings:
            score -= 0.05
            if report.overall_compatibility == CompatibilityLevel.COMPATIBLE:
                report.overall_compatibility = CompatibilityLevel.WARNING
        
        report.compatibility_score = max(score, 0.0)
    
    def _generate_recommendations(self, report: CompatibilityReport):
        """生成总体建议。"""
        if report.overall_compatibility == CompatibilityLevel.CRITICAL:
            report.recommendations.append("存在严重兼容性问题，无法执行任务")
            report.recommendations.append("请解决所有关键问题后重新检查")
        elif report.overall_compatibility == CompatibilityLevel.ERROR:
            report.recommendations.append("存在兼容性错误，需要修正后才能执行任务")
            report.recommendations.append("建议使用自动修复功能或手动调整参数")
        elif report.overall_compatibility == CompatibilityLevel.WARNING:
            report.recommendations.append("存在兼容性警告，建议优化参数以获得更好性能")
            report.recommendations.append("可以执行任务，但需要注意相关风险")
        else:
            report.recommendations.append("兼容性检查通过，可以安全执行任务")
        
        # 基于问题类别生成具体建议
        categories = set(issue.category for issue in report.issues + report.warnings)
        
        if IssueCategory.BATTERY_LIFE in categories:
            report.recommendations.append("考虑准备备用电池或分割长航线")
        
        if IssueCategory.WEATHER_CONDITIONS in categories:
            report.recommendations.append("密切关注天气变化，必要时推迟任务")
        
        if IssueCategory.PAYLOAD_COMPATIBILITY in categories:
            report.recommendations.append("验证负载安装和配置是否正确")
    
    def _generate_auto_fixes(
        self,
        aircraft_specs: AircraftSpecs,
        mission_config: Dict[str, Any],
        report: CompatibilityReport
    ):
        """生成自动修复建议。"""
        auto_fixes = {}
        
        for issue in report.issues:
            if issue.auto_fix_available and issue.fix_parameters:
                auto_fixes.update(issue.fix_parameters)
        
        # 添加优化建议
        if "flight_height" not in auto_fixes:
            current_height = mission_config.get("flight_height", 100.0)
            recommended_height = min(current_height, self.parameter_limits["flight_height"]["recommended_max"])
            if recommended_height != current_height:
                auto_fixes["flight_height"] = recommended_height
        
        if "flight_speed" not in auto_fixes:
            current_speed = mission_config.get("flight_speed", 5.0)
            recommended_speed = min(current_speed, self.parameter_limits["flight_speed"]["recommended_max"])
            if recommended_speed != current_speed:
                auto_fixes["flight_speed"] = recommended_speed
        
        report.auto_fixes = auto_fixes
    
    def apply_auto_fixes(
        self,
        mission_config: Dict[str, Any],
        auto_fixes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """应用自动修复。"""
        fixed_config = mission_config.copy()
        fixed_config.update(auto_fixes)
        return fixed_config
    
    def get_parameter_recommendations(self, aircraft_id: str) -> Dict[str, Any]:
        """获取参数建议。"""
        aircraft_specs = self.database.get_aircraft_specs(aircraft_id)
        if not aircraft_specs:
            return {}
        
        recommendations = {
            "flight_height": {
                "min": 10,
                "max": min(aircraft_specs.flight_specs.max_altitude, 500),
                "recommended": min(120, aircraft_specs.flight_specs.max_altitude * 0.8),
                "unit": "meters"
            },
            "flight_speed": {
                "min": 1,
                "max": aircraft_specs.flight_specs.max_speed,
                "recommended": min(8, aircraft_specs.flight_specs.max_speed * 0.7),
                "unit": "m/s"
            },
            "max_flight_time": {
                "value": aircraft_specs.flight_specs.max_flight_time,
                "safe_limit": aircraft_specs.flight_specs.max_flight_time * 0.8,
                "unit": "minutes"
            }
        }
        
        if aircraft_specs.integrated_gimbal:
            recommendations["gimbal_pitch"] = {
                "min": aircraft_specs.integrated_gimbal.pitch_range[0],
                "max": aircraft_specs.integrated_gimbal.pitch_range[1],
                "recommended": -90,
                "unit": "degrees"
            }
        
        return recommendations


# 全局兼容性检查器实例
compatibility_checker = CompatibilityChecker()
"""
大疆无人机设备数据库。
包含支持的无人机型号、规格参数和负载配置信息。
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from ..models.aircraft import AircraftModel, PayloadModel


@dataclass
class CameraSpecs:
    """相机规格参数。"""
    sensor_width: float  # 传感器宽度(mm)
    sensor_height: float  # 传感器高度(mm)
    focal_length: float  # 焦距(mm)
    image_width: int     # 图像宽度(像素)
    image_height: int    # 图像高度(像素)
    pixel_size: float    # 像素尺寸(μm)
    iso_range: tuple     # ISO范围
    shutter_speed_range: tuple  # 快门速度范围
    aperture_range: tuple       # 光圈范围
    video_resolution: List[str] = field(default_factory=list)  # 视频分辨率
    photo_formats: List[str] = field(default_factory=list)     # 照片格式
    
    def calculate_ground_resolution(self, flight_height: float) -> float:
        """计算地面分辨率(cm/pixel)。"""
        return (self.sensor_width * flight_height) / (self.focal_length * self.image_width) * 100


@dataclass
class GimbalSpecs:
    """云台规格参数。"""
    pitch_range: tuple   # 俯仰角范围(度)
    yaw_range: tuple     # 偏航角范围(度)
    roll_range: tuple    # 横滚角范围(度)
    pitch_speed: float   # 俯仰速度(度/秒)
    yaw_speed: float     # 偏航速度(度/秒)
    roll_speed: float    # 横滚速度(度/秒)
    stabilization_modes: List[str] = field(default_factory=list)  # 稳定模式
    follow_modes: List[str] = field(default_factory=list)         # 跟随模式


@dataclass
class FlightSpecs:
    """飞行性能规格。"""
    max_flight_time: float      # 最大飞行时间(分钟)
    max_flight_distance: float  # 最大飞行距离(km)
    max_altitude: float         # 最大飞行高度(m)
    max_speed: float           # 最大飞行速度(m/s)
    max_ascent_speed: float    # 最大上升速度(m/s)
    max_descent_speed: float   # 最大下降速度(m/s)
    wind_resistance: float     # 抗风能力(m/s)
    operating_temperature: tuple  # 工作温度范围(°C)
    positioning_accuracy: float   # 定位精度(m)
    hover_accuracy: float        # 悬停精度(m)


@dataclass
class BatterySpecs:
    """电池规格参数。"""
    capacity: float        # 电池容量(mAh)
    voltage: float         # 电压(V)
    type: str             # 电池类型
    charging_time: float  # 充电时间(分钟)
    cycle_life: int       # 循环寿命
    operating_temperature: tuple  # 工作温度范围(°C)
    weight: float         # 重量(g)


@dataclass
class PhysicalSpecs:
    """物理规格参数。"""
    dimensions: tuple     # 尺寸(长x宽x高, mm)
    weight: float         # 重量(g)
    folded_dimensions: Optional[tuple] = None  # 折叠尺寸(mm)
    max_takeoff_weight: Optional[float] = None  # 最大起飞重量(g)
    protection_rating: Optional[str] = None     # 防护等级


@dataclass
class PayloadSpecs:
    """负载规格参数。"""
    payload_id: str
    name: str
    type: str  # camera, lidar, multispectral, thermal
    weight: float  # 重量(g)
    power_consumption: float  # 功耗(W)
    mount_position: str  # 挂载位置
    camera_specs: Optional[CameraSpecs] = None
    gimbal_specs: Optional[GimbalSpecs] = None
    additional_specs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AircraftSpecs:
    """完整的无人机规格参数。"""
    aircraft_id: str
    model_name: str
    manufacturer: str
    category: str  # consumer, professional, enterprise
    release_year: int
    
    # 核心规格
    flight_specs: FlightSpecs
    battery_specs: BatterySpecs
    physical_specs: PhysicalSpecs
    
    # 负载和云台
    supported_payloads: List[PayloadSpecs]
    integrated_camera: Optional[CameraSpecs] = None
    integrated_gimbal: Optional[GimbalSpecs] = None
    
    # 飞行模式和功能
    flight_modes: List[str] = field(default_factory=list)
    intelligent_features: List[str] = field(default_factory=list)
    safety_features: List[str] = field(default_factory=list)
    
    # 连接和控制
    transmission_range: float = 0.0  # 图传距离(km)
    control_range: float = 0.0       # 控制距离(km)
    supported_frequencies: List[str] = field(default_factory=list)
    
    # 其他参数
    metadata: Dict[str, Any] = field(default_factory=dict)


class AircraftDatabase:
    """无人机数据库。"""
    
    def __init__(self):
        """初始化数据库。"""
        self._aircraft_specs: Dict[str, AircraftSpecs] = {}
        self._payload_specs: Dict[str, PayloadSpecs] = {}
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化数据库数据。"""
        # M300 RTK系列
        self._add_m300_rtk()
        
        # M350 RTK系列
        self._add_m350_rtk()
        
        # M30系列
        self._add_m30_series()
        
        # M3系列
        self._add_m3_series()
        
        # 添加负载数据
        self._add_payload_specs()
    
    def _add_m300_rtk(self):
        """添加M300 RTK规格。"""
        # 飞行性能
        flight_specs = FlightSpecs(
            max_flight_time=55.0,
            max_flight_distance=15.0,
            max_altitude=7000.0,
            max_speed=23.0,
            max_ascent_speed=6.0,
            max_descent_speed=5.0,
            wind_resistance=15.0,
            operating_temperature=(-20, 50),
            positioning_accuracy=0.1,
            hover_accuracy=0.1
        )
        
        # 电池规格
        battery_specs = BatterySpecs(
            capacity=5935,
            voltage=26.1,
            type="TB60",
            charging_time=60,
            cycle_life=400,
            operating_temperature=(-20, 40),
            weight=1353
        )
        
        # 物理规格
        physical_specs = PhysicalSpecs(
            dimensions=(810, 670, 430),
            weight=6300,
            folded_dimensions=(430, 420, 430),
            max_takeoff_weight=9000,
            protection_rating="IP45"
        )
        
        # 云台规格
        gimbal_specs = GimbalSpecs(
            pitch_range=(-120, 45),
            yaw_range=(-320, 320),
            roll_range=(-45, 45),
            pitch_speed=90,
            yaw_speed=90,
            roll_speed=90,
            stabilization_modes=["FPV", "Follow", "Lock"],
            follow_modes=["FPV", "Follow", "Lock"]
        )
        
        aircraft_specs = AircraftSpecs(
            aircraft_id="M300_RTK",
            model_name="Matrice 300 RTK",
            manufacturer="DJI",
            category="enterprise",
            release_year=2020,
            flight_specs=flight_specs,
            battery_specs=battery_specs,
            physical_specs=physical_specs,
            supported_payloads=[],  # 将在后面添加
            integrated_gimbal=gimbal_specs,
            flight_modes=[
                "Position", "Attitude", "Sport", "Tripod", 
                "Cinematic", "Normal", "Gentle"
            ],
            intelligent_features=[
                "ActiveTrack", "Point of Interest", "Waypoint",
                "TapFly", "Terrain Follow", "Advanced Pilot Assistance System"
            ],
            safety_features=[
                "Obstacle Sensing", "Return-to-Home", "Failsafe",
                "Redundant IMU", "Redundant Compass", "ADS-B"
            ],
            transmission_range=15.0,
            control_range=15.0,
            supported_frequencies=["2.4GHz", "5.8GHz"],
            metadata={
                "rtk_positioning": True,
                "dual_operator": True,
                "night_flight_capable": True,
                "ip_rating": "IP45"
            }
        )
        
        self._aircraft_specs["M300_RTK"] = aircraft_specs
    
    def _add_m350_rtk(self):
        """添加M350 RTK规格。"""
        # 飞行性能
        flight_specs = FlightSpecs(
            max_flight_time=55.0,
            max_flight_distance=15.0,
            max_altitude=7000.0,
            max_speed=23.0,
            max_ascent_speed=6.0,
            max_descent_speed=5.0,
            wind_resistance=12.0,
            operating_temperature=(-20, 50),
            positioning_accuracy=0.1,
            hover_accuracy=0.1
        )
        
        # 电池规格
        battery_specs = BatterySpecs(
            capacity=5935,
            voltage=26.1,
            type="TB65",
            charging_time=60,
            cycle_life=400,
            operating_temperature=(-20, 40),
            weight=1353
        )
        
        # 物理规格
        physical_specs = PhysicalSpecs(
            dimensions=(895, 678, 378),
            weight=6400,
            folded_dimensions=(430, 420, 430),
            max_takeoff_weight=9200,
            protection_rating="IP55"
        )
        
        # 云台规格
        gimbal_specs = GimbalSpecs(
            pitch_range=(-120, 45),
            yaw_range=(-320, 320),
            roll_range=(-45, 45),
            pitch_speed=90,
            yaw_speed=90,
            roll_speed=90,
            stabilization_modes=["FPV", "Follow", "Lock"],
            follow_modes=["FPV", "Follow", "Lock"]
        )
        
        aircraft_specs = AircraftSpecs(
            aircraft_id="M350_RTK",
            model_name="Matrice 350 RTK",
            manufacturer="DJI",
            category="enterprise",
            release_year=2022,
            flight_specs=flight_specs,
            battery_specs=battery_specs,
            physical_specs=physical_specs,
            supported_payloads=[],
            integrated_gimbal=gimbal_specs,
            flight_modes=[
                "Position", "Attitude", "Sport", "Tripod", 
                "Cinematic", "Normal", "Gentle"
            ],
            intelligent_features=[
                "ActiveTrack", "Point of Interest", "Waypoint",
                "TapFly", "Terrain Follow", "Advanced Pilot Assistance System",
                "O3 Enterprise Transmission"
            ],
            safety_features=[
                "Omnidirectional Obstacle Sensing", "Return-to-Home", 
                "Failsafe", "Redundant IMU", "Redundant Compass", 
                "ADS-B", "Health Management System"
            ],
            transmission_range=20.0,
            control_range=20.0,
            supported_frequencies=["2.4GHz", "5.8GHz", "900MHz"],
            metadata={
                "rtk_positioning": True,
                "dual_operator": True,
                "night_flight_capable": True,
                "ip_rating": "IP55",
                "o3_transmission": True
            }
        )
        
        self._aircraft_specs["M350_RTK"] = aircraft_specs
    
    def _add_m30_series(self):
        """添加M30系列规格。"""
        # M30通用规格
        base_flight_specs = FlightSpecs(
            max_flight_time=41.0,
            max_flight_distance=18.0,
            max_altitude=7000.0,
            max_speed=23.0,
            max_ascent_speed=6.0,
            max_descent_speed=6.0,
            wind_resistance=15.0,
            operating_temperature=(-20, 50),
            positioning_accuracy=0.1,
            hover_accuracy=0.1
        )
        
        base_battery_specs = BatterySpecs(
            capacity=5880,
            voltage=25.2,
            type="TB30",
            charging_time=90,
            cycle_life=400,
            operating_temperature=(-20, 40),
            weight=1355
        )
        
        base_physical_specs = PhysicalSpecs(
            dimensions=(365, 295, 215),
            weight=3700,
            folded_dimensions=(365, 215, 195),
            max_takeoff_weight=3700,
            protection_rating="IP55"
        )
        
        # M30相机规格
        m30_camera = CameraSpecs(
            sensor_width=23.5,
            sensor_height=15.6,
            focal_length=24.0,
            image_width=5472,
            image_height=3648,
            pixel_size=4.3,
            iso_range=(100, 6400),
            shutter_speed_range=(1/8000, 8),
            aperture_range=(2.8, 11),
            video_resolution=["4K/30fps", "2.7K/30fps", "FHD/60fps"],
            photo_formats=["JPEG", "DNG"]
        )
        
        # M30云台规格
        m30_gimbal = GimbalSpecs(
            pitch_range=(-90, 35),
            yaw_range=(-95, 95),
            roll_range=(-45, 45),
            pitch_speed=100,
            yaw_speed=100,
            roll_speed=100,
            stabilization_modes=["FPV", "Follow", "Lock"],
            follow_modes=["FPV", "Follow", "Lock"]
        )
        
        # M30
        m30_specs = AircraftSpecs(
            aircraft_id="M30",
            model_name="Matrice 30",
            manufacturer="DJI",
            category="enterprise",
            release_year=2022,
            flight_specs=base_flight_specs,
            battery_specs=base_battery_specs,
            physical_specs=base_physical_specs,
            supported_payloads=[],
            integrated_camera=m30_camera,
            integrated_gimbal=m30_gimbal,
            flight_modes=[
                "Position", "Attitude", "Sport", "Tripod", 
                "Cinematic", "Normal"
            ],
            intelligent_features=[
                "ActiveTrack", "Point of Interest", "Waypoint",
                "Smart Low Battery Return", "Precise Landing"
            ],
            safety_features=[
                "Omnidirectional Obstacle Sensing", "Return-to-Home",
                "Failsafe", "ADS-B", "Night Vision FPV"
            ],
            transmission_range=18.0,
            control_range=18.0,
            supported_frequencies=["2.4GHz", "5.8GHz"],
            metadata={
                "rtk_positioning": True,
                "night_vision": False,
                "thermal_camera": False,
                "ip_rating": "IP55"
            }
        )
        
        # M30T (带热成像)
        m30t_specs = AircraftSpecs(
            aircraft_id="M30T",
            model_name="Matrice 30T",
            manufacturer="DJI",
            category="enterprise",
            release_year=2022,
            flight_specs=base_flight_specs,
            battery_specs=base_battery_specs,
            physical_specs=base_physical_specs,
            supported_payloads=[],
            integrated_camera=m30_camera,
            integrated_gimbal=m30_gimbal,
            flight_modes=m30_specs.flight_modes,
            intelligent_features=m30_specs.intelligent_features,
            safety_features=m30_specs.safety_features,
            transmission_range=18.0,
            control_range=18.0,
            supported_frequencies=["2.4GHz", "5.8GHz"],
            metadata={
                "rtk_positioning": True,
                "night_vision": True,
                "thermal_camera": True,
                "ip_rating": "IP55"
            }
        )
        
        self._aircraft_specs["M30"] = m30_specs
        self._aircraft_specs["M30T"] = m30t_specs
    
    def _add_m3_series(self):
        """添加M3系列规格。"""
        # M3E
        m3e_flight_specs = FlightSpecs(
            max_flight_time=45.0,
            max_flight_distance=32.0,
            max_altitude=6000.0,
            max_speed=21.0,
            max_ascent_speed=6.0,
            max_descent_speed=6.0,
            wind_resistance=12.0,
            operating_temperature=(-10, 40),
            positioning_accuracy=0.3,
            hover_accuracy=0.1
        )
        
        m3e_battery_specs = BatterySpecs(
            capacity=5000,
            voltage=15.4,
            type="Intelligent Flight Battery",
            charging_time=96,
            cycle_life=500,
            operating_temperature=(-10, 40),
            weight=335
        )
        
        m3e_physical_specs = PhysicalSpecs(
            dimensions=(347, 283, 107),
            weight=1050,
            folded_dimensions=(221, 96, 90),
            max_takeoff_weight=1050,
            protection_rating=None
        )
        
        m3e_camera = CameraSpecs(
            sensor_width=17.3,
            sensor_height=13.0,
            focal_length=24.0,
            image_width=5280,
            image_height=3956,
            pixel_size=3.3,
            iso_range=(100, 6400),
            shutter_speed_range=(1/8000, 8),
            aperture_range=(2.8, 11),
            video_resolution=["4K/60fps", "2.7K/60fps", "FHD/120fps"],
            photo_formats=["JPEG", "DNG"]
        )
        
        m3e_gimbal = GimbalSpecs(
            pitch_range=(-90, 35),
            yaw_range=(-95, 95),
            roll_range=(-35, 35),
            pitch_speed=100,
            yaw_speed=100,
            roll_speed=100,
            stabilization_modes=["FPV", "Follow", "Lock"],
            follow_modes=["FPV", "Follow", "Lock"]
        )
        
        m3e_specs = AircraftSpecs(
            aircraft_id="M3E",
            model_name="Mavic 3 Enterprise",
            manufacturer="DJI",
            category="enterprise",
            release_year=2022,
            flight_specs=m3e_flight_specs,
            battery_specs=m3e_battery_specs,
            physical_specs=m3e_physical_specs,
            supported_payloads=[],
            integrated_camera=m3e_camera,
            integrated_gimbal=m3e_gimbal,
            flight_modes=[
                "Position", "Attitude", "Sport", "Tripod", 
                "Cinematic", "Normal"
            ],
            intelligent_features=[
                "ActiveTrack", "Point of Interest", "Waypoint",
                "QuickShots", "Hyperlapse", "Panorama"
            ],
            safety_features=[
                "Omnidirectional Obstacle Sensing", "APAS 5.0",
                "Return-to-Home", "Failsafe"
            ],
            transmission_range=32.0,
            control_range=32.0,
            supported_frequencies=["2.4GHz", "5.8GHz"],
            metadata={
                "rtk_positioning": True,
                "mechanical_shutter": True,
                "ip_rating": None
            }
        )
        
        # 其他M3系列型号可以类似添加
        self._aircraft_specs["M3E"] = m3e_specs
    
    def _add_payload_specs(self):
        """添加负载规格。"""
        # Zenmuse H20系列
        h20_camera = CameraSpecs(
            sensor_width=23.5,
            sensor_height=15.6,
            focal_length=85.0,
            image_width=5472,
            image_height=3648,
            pixel_size=4.3,
            iso_range=(100, 25600),
            shutter_speed_range=(1/8000, 8),
            aperture_range=(2.8, 11),
            video_resolution=["4K/30fps", "2.7K/30fps", "FHD/60fps"],
            photo_formats=["JPEG", "DNG"]
        )
        
        h20_gimbal = GimbalSpecs(
            pitch_range=(-120, 30),
            yaw_range=(-320, 320),
            roll_range=(-20, 20),
            pitch_speed=90,
            yaw_speed=90,
            roll_speed=90,
            stabilization_modes=["FPV", "Follow", "Lock"],
            follow_modes=["FPV", "Follow", "Lock"]
        )
        
        h20_payload = PayloadSpecs(
            payload_id="H20",
            name="Zenmuse H20",
            type="camera",
            weight=828,
            power_consumption=18,
            mount_position="gimbal",
            camera_specs=h20_camera,
            gimbal_specs=h20_gimbal,
            additional_specs={
                "zoom_range": "1x-23x",
                "thermal_camera": False,
                "laser_rangefinder": True,
                "night_vision": False
            }
        )
        
        # Zenmuse H20T
        h20t_payload = PayloadSpecs(
            payload_id="H20T",
            name="Zenmuse H20T",
            type="camera",
            weight=828,
            power_consumption=18,
            mount_position="gimbal",
            camera_specs=h20_camera,
            gimbal_specs=h20_gimbal,
            additional_specs={
                "zoom_range": "1x-23x",
                "thermal_camera": True,
                "thermal_resolution": "640x512",
                "laser_rangefinder": True,
                "night_vision": True
            }
        )
        
        # Zenmuse P1
        p1_camera = CameraSpecs(
            sensor_width=35.9,
            sensor_height=24.0,
            focal_length=35.0,
            image_width=8192,
            image_height=5460,
            pixel_size=4.4,
            iso_range=(100, 25600),
            shutter_speed_range=(1/2000, 8),
            aperture_range=(2.8, 11),
            video_resolution=["4K/60fps"],
            photo_formats=["JPEG", "DNG"]
        )
        
        p1_gimbal = GimbalSpecs(
            pitch_range=(-90, 20),
            yaw_range=(-320, 320),
            roll_range=(-20, 20),
            pitch_speed=90,
            yaw_speed=90,
            roll_speed=90,
            stabilization_modes=["FPV", "Follow", "Lock"],
            follow_modes=["FPV", "Follow", "Lock"]
        )
        
        p1_payload = PayloadSpecs(
            payload_id="P1",
            name="Zenmuse P1",
            type="camera",
            weight=740,
            power_consumption=14,
            mount_position="gimbal",
            camera_specs=p1_camera,
            gimbal_specs=p1_gimbal,
            additional_specs={
                "full_frame_sensor": True,
                "mechanical_shutter": True,
                "interchangeable_lens": True,
                "rtk_sync": True
            }
        )
        
        # 存储负载规格
        self._payload_specs["H20"] = h20_payload
        self._payload_specs["H20T"] = h20t_payload
        self._payload_specs["P1"] = p1_payload
        
        # 更新飞机支持的负载
        if "M300_RTK" in self._aircraft_specs:
            self._aircraft_specs["M300_RTK"].supported_payloads = [
                h20_payload, h20t_payload, p1_payload
            ]
        
        if "M350_RTK" in self._aircraft_specs:
            self._aircraft_specs["M350_RTK"].supported_payloads = [
                h20_payload, h20t_payload, p1_payload
            ]
    
    def get_aircraft_specs(self, aircraft_id: str) -> Optional[AircraftSpecs]:
        """获取无人机规格。"""
        return self._aircraft_specs.get(aircraft_id)
    
    def get_payload_specs(self, payload_id: str) -> Optional[PayloadSpecs]:
        """获取负载规格。"""
        return self._payload_specs.get(payload_id)
    
    def get_all_aircraft(self) -> List[AircraftSpecs]:
        """获取所有无人机规格。"""
        return list(self._aircraft_specs.values())
    
    def get_all_payloads(self) -> List[PayloadSpecs]:
        """获取所有负载规格。"""
        return list(self._payload_specs.values())
    
    def get_aircraft_by_category(self, category: str) -> List[AircraftSpecs]:
        """按类别获取无人机。"""
        return [
            specs for specs in self._aircraft_specs.values()
            if specs.category == category
        ]
    
    def get_compatible_payloads(self, aircraft_id: str) -> List[PayloadSpecs]:
        """获取兼容的负载。"""
        aircraft_specs = self.get_aircraft_specs(aircraft_id)
        if aircraft_specs:
            return aircraft_specs.supported_payloads
        return []
    
    def search_aircraft(self, **criteria) -> List[AircraftSpecs]:
        """搜索无人机。"""
        results = []
        
        for specs in self._aircraft_specs.values():
            match = True
            
            # 检查搜索条件
            for key, value in criteria.items():
                if key == "max_flight_time" and specs.flight_specs.max_flight_time < value:
                    match = False
                    break
                elif key == "max_altitude" and specs.flight_specs.max_altitude < value:
                    match = False
                    break
                elif key == "category" and specs.category != value:
                    match = False
                    break
                elif key == "manufacturer" and specs.manufacturer != value:
                    match = False
                    break
                elif key == "rtk_positioning" and specs.metadata.get("rtk_positioning") != value:
                    match = False
                    break
            
            if match:
                results.append(specs)
        
        return results
    
    def get_aircraft_capabilities(self, aircraft_id: str) -> Dict[str, Any]:
        """获取无人机能力摘要。"""
        specs = self.get_aircraft_specs(aircraft_id)
        if not specs:
            return {}
        
        return {
            "model_name": specs.model_name,
            "category": specs.category,
            "max_flight_time": specs.flight_specs.max_flight_time,
            "max_altitude": specs.flight_specs.max_altitude,
            "max_speed": specs.flight_specs.max_speed,
            "transmission_range": specs.transmission_range,
            "rtk_positioning": specs.metadata.get("rtk_positioning", False),
            "obstacle_sensing": "Obstacle Sensing" in specs.safety_features,
            "supported_payload_count": len(specs.supported_payloads),
            "integrated_camera": specs.integrated_camera is not None,
            "protection_rating": specs.physical_specs.protection_rating
        }


# 全局数据库实例
aircraft_database = AircraftDatabase()
"""
多航线协调工具的单元测试。
"""

import pytest
from unittest.mock import patch, MagicMock

from dji_waypoint_mcp.tools.multi_flight_coordinator import (
    MultiFlightCoordinator,
    MultiFlightInput,
    FlightConfiguration,
    FlightPriority,
    FlightSequenceMode
)
from dji_waypoint_mcp.models import (
    Coordinates,
    Waypoint,
    FlightPath,
    HeightMode
)


class TestMultiFlightInput:
    """多航线输入参数测试。"""
    
    def test_valid_multi_flight_input(self):
        """测试有效的多航线输入。"""
        flight_configs = [
            {
                "flight_id": "flight_1",
                "flight_path": {
                    "waypoints": [
                        {
                            "index": 0,
                            "coordinates": {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                            "speed": 5.0
                        }
                    ],
                    "global_speed": 5.0,
                    "global_height": 100.0
                },
                "priority": "high"
            }
        ]
        
        multi_flight_input = MultiFlightInput(flight_configurations=flight_configs)
        
        assert len(multi_flight_input.flight_configurations) == 1
        assert multi_flight_input.sequence_mode == FlightSequenceMode.OPTIMIZED
        assert multi_flight_input.max_flight_time == 25.0
        assert multi_flight_input.battery_reserve == 20.0
        assert multi_flight_input.transition_time == 2.0
        assert multi_flight_input.quality_threshold == 0.8
        assert multi_flight_input.optimize_battery_usage is True
        assert multi_flight_input.merge_compatible_flights is False
    
    def test_empty_flight_configurations(self):
        """测试空航线配置。"""
        with pytest.raises(Exception):
            MultiFlightInput(flight_configurations=[])
    
    def test_custom_parameters(self):
        """测试自定义参数。"""
        flight_configs = [
            {
                "flight_id": "test_flight",
                "flight_path": {
                    "waypoints": [
                        {
                            "index": 0,
                            "coordinates": {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                            "speed": 5.0
                        }
                    ]
                }
            }
        ]
        
        multi_flight_input = MultiFlightInput(
            flight_configurations=flight_configs,
            sequence_mode=FlightSequenceMode.SEQUENTIAL,
            max_flight_time=20.0,
            battery_reserve=30.0,
            transition_time=3.0,
            quality_threshold=0.9,
            optimize_battery_usage=False,
            merge_compatible_flights=True
        )
        
        assert multi_flight_input.sequence_mode == FlightSequenceMode.SEQUENTIAL
        assert multi_flight_input.max_flight_time == 20.0
        assert multi_flight_input.battery_reserve == 30.0
        assert multi_flight_input.transition_time == 3.0
        assert multi_flight_input.quality_threshold == 0.9
        assert multi_flight_input.optimize_battery_usage is False
        assert multi_flight_input.merge_compatible_flights is True


class TestFlightConfiguration:
    """航线配置测试。"""
    
    def test_flight_configuration_creation(self):
        """测试航线配置创建。"""
        waypoints = [
            Waypoint(
                index=0,
                coordinates=Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0),
                speed=5.0
            )
        ]
        
        flight_path = FlightPath(
            waypoints=waypoints,
            global_speed=5.0,
            global_height=100.0,
            height_mode=HeightMode.EGM96
        )
        
        config = FlightConfiguration(
            flight_id="test_flight",
            flight_path=flight_path,
            priority=FlightPriority.HIGH,
            estimated_duration=10.0,
            battery_consumption=25.0,
            photo_count=50,
            coverage_area=5.0,
            gimbal_angles={"pitch": -90.0, "yaw": 0.0},
            metadata={"test": "data"}
        )
        
        assert config.flight_id == "test_flight"
        assert config.priority == FlightPriority.HIGH
        assert config.estimated_duration == 10.0
        assert config.battery_consumption == 25.0
        assert config.photo_count == 50
        assert config.coverage_area == 5.0
        assert config.gimbal_angles["pitch"] == -90.0
        assert config.metadata["test"] == "data"


class TestMultiFlightCoordinator:
    """多航线协调工具测试。"""
    
    def setup_method(self):
        """设置测试环境。"""
        self.coordinator = MultiFlightCoordinator()
        
        # 创建测试航线配置
        self.test_flight_configs = [
            {
                "flight_id": "flight_nadir",
                "flight_path": {
                    "waypoints": [
                        {
                            "index": 0,
                            "coordinates": {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                            "speed": 5.0,
                            "gimbal_pitch_angle": -90.0
                        },
                        {
                            "index": 1,
                            "coordinates": {"latitude": 40.7228, "longitude": -74.0060, "altitude": 100.0},
                            "speed": 5.0,
                            "gimbal_pitch_angle": -90.0
                        }
                    ],
                    "global_speed": 5.0,
                    "global_height": 100.0
                },
                "priority": "high",
                "gimbal_pitch": -90.0,
                "gimbal_yaw": 0.0,
                "photo_interval": 2.0,
                "flight_speed": 5.0
            },
            {
                "flight_id": "flight_oblique",
                "flight_path": {
                    "waypoints": [
                        {
                            "index": 0,
                            "coordinates": {"latitude": 40.7128, "longitude": -74.0160, "altitude": 100.0},
                            "speed": 5.0,
                            "gimbal_pitch_angle": -45.0
                        },
                        {
                            "index": 1,
                            "coordinates": {"latitude": 40.7228, "longitude": -74.0160, "altitude": 100.0},
                            "speed": 5.0,
                            "gimbal_pitch_angle": -45.0
                        }
                    ],
                    "global_speed": 5.0,
                    "global_height": 100.0
                },
                "priority": "medium",
                "gimbal_pitch": -45.0,
                "gimbal_yaw": 0.0,
                "photo_interval": 2.0,
                "flight_speed": 5.0
            }
        ]
    
    def test_tool_definition(self):
        """测试工具定义。"""
        tool_def = self.coordinator.get_tool_definition()
        
        assert tool_def.name == "coordinate_multi_flights"
        assert "协调和管理多条航线" in tool_def.description
        assert tool_def.inputSchema is not None
        assert "flight_configurations" in tool_def.inputSchema["properties"]
        assert "sequence_mode" in tool_def.inputSchema["properties"]
        assert tool_def.inputSchema["required"] == ["flight_configurations"]
    
    @pytest.mark.asyncio
    async def test_successful_coordination(self):
        """测试成功的多航线协调。"""
        arguments = {
            "flight_configurations": self.test_flight_configs,
            "sequence_mode": "optimized",
            "max_flight_time": 25.0,
            "battery_reserve": 20.0
        }
        
        result = await self.coordinator.execute(arguments)
        
        assert result["success"] is True
        assert "成功协调" in result["message"]
        assert "coordination_plan" in result["data"]
        assert "flight_sequence" in result["data"]
        assert "battery_plan" in result["data"]
        assert "quality_report" in result["data"]
        assert "overall_statistics" in result["data"]
        
        # 检查协调计划
        plan = result["data"]["coordination_plan"]
        assert "execution_mode" in plan
        assert "flight_batches" in plan
        assert "total_execution_time" in plan
        assert "quality_status" in plan
        
        # 检查航线序列
        sequence = result["data"]["flight_sequence"]
        assert len(sequence) == 2
        assert all("flight_id" in flight for flight in sequence)
        assert all("priority" in flight for flight in sequence)
        
        # 检查电池计划
        battery_plan = result["data"]["battery_plan"]
        assert "flight_batches" in battery_plan
        assert "total_batteries_needed" in battery_plan
        assert "total_flight_time" in battery_plan
    
    @pytest.mark.asyncio
    async def test_sequential_mode(self):
        """测试顺序执行模式。"""
        arguments = {
            "flight_configurations": self.test_flight_configs,
            "sequence_mode": "sequential"
        }
        
        result = await self.coordinator.execute(arguments)
        
        assert result["success"] is True
        plan = result["data"]["coordination_plan"]
        assert plan["execution_mode"] == "sequential"
    
    @pytest.mark.asyncio
    async def test_parallel_mode(self):
        """测试并行执行模式。"""
        arguments = {
            "flight_configurations": self.test_flight_configs,
            "sequence_mode": "parallel"
        }
        
        result = await self.coordinator.execute(arguments)
        
        assert result["success"] is True
        plan = result["data"]["coordination_plan"]
        assert plan["execution_mode"] == "parallel"
    
    @pytest.mark.asyncio
    async def test_merge_compatible_flights(self):
        """测试合并兼容航线。"""
        # 创建两个兼容的航线（相同参数）
        compatible_configs = [
            {
                "flight_id": "flight_1",
                "flight_path": {
                    "waypoints": [
                        {
                            "index": 0,
                            "coordinates": {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                            "speed": 5.0,
                            "gimbal_pitch_angle": -90.0
                        }
                    ],
                    "global_speed": 5.0,
                    "global_height": 100.0
                },
                "gimbal_pitch": -90.0,
                "gimbal_yaw": 0.0,
                "flight_speed": 5.0
            },
            {
                "flight_id": "flight_2",
                "flight_path": {
                    "waypoints": [
                        {
                            "index": 0,
                            "coordinates": {"latitude": 40.7228, "longitude": -74.0060, "altitude": 100.0},
                            "speed": 5.0,
                            "gimbal_pitch_angle": -90.0
                        }
                    ],
                    "global_speed": 5.0,
                    "global_height": 100.0
                },
                "gimbal_pitch": -90.0,
                "gimbal_yaw": 0.0,
                "flight_speed": 5.0
            }
        ]
        
        arguments = {
            "flight_configurations": compatible_configs,
            "merge_compatible_flights": True
        }
        
        result = await self.coordinator.execute(arguments)
        
        assert result["success"] is True
        # 检查兼容性报告
        compatibility = result["data"]["compatibility_report"]
        assert "compatible_groups" in compatibility
        assert "conflicts" in compatibility
    
    @pytest.mark.asyncio
    async def test_battery_optimization(self):
        """测试电池优化。"""
        # 创建高电池消耗的航线配置
        high_consumption_configs = [
            {
                "flight_id": "long_flight_1",
                "flight_path": {
                    "waypoints": [
                        {
                            "index": i,
                            "coordinates": {
                                "latitude": 40.7128 + i * 0.001,
                                "longitude": -74.0060 + i * 0.001,
                                "altitude": 100.0
                            },
                            "speed": 5.0
                        }
                        for i in range(20)  # 20个航点，模拟长航线
                    ],
                    "global_speed": 5.0,
                    "global_height": 100.0
                },
                "flight_speed": 5.0
            },
            {
                "flight_id": "long_flight_2",
                "flight_path": {
                    "waypoints": [
                        {
                            "index": i,
                            "coordinates": {
                                "latitude": 40.7228 + i * 0.001,
                                "longitude": -74.0160 + i * 0.001,
                                "altitude": 100.0
                            },
                            "speed": 5.0
                        }
                        for i in range(20)  # 20个航点，模拟长航线
                    ],
                    "global_speed": 5.0,
                    "global_height": 100.0
                },
                "flight_speed": 5.0
            }
        ]
        
        arguments = {
            "flight_configurations": high_consumption_configs,
            "optimize_battery_usage": True,
            "max_flight_time": 15.0,  # 较短的最大飞行时间
            "battery_reserve": 25.0   # 较高的电池预留
        }
        
        result = await self.coordinator.execute(arguments)
        
        assert result["success"] is True
        battery_plan = result["data"]["battery_plan"]
        
        # 应该需要多个电池批次
        assert battery_plan["total_batteries_needed"] >= 1
        assert len(battery_plan["flight_batches"]) >= 1
    
    @pytest.mark.asyncio
    async def test_quality_control(self):
        """测试质量控制。"""
        # 创建质量问题的航线配置
        poor_quality_configs = [
            {
                "flight_id": "poor_flight",
                "flight_path": {
                    "waypoints": [
                        {
                            "index": 0,
                            "coordinates": {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100.0},
                            "speed": 5.0
                        }
                        # 只有一个航点，质量较差
                    ],
                    "global_speed": 5.0,
                    "global_height": 100.0
                },
                "flight_speed": 5.0
            }
        ]
        
        arguments = {
            "flight_configurations": poor_quality_configs,
            "quality_threshold": 0.8
        }
        
        result = await self.coordinator.execute(arguments)
        
        assert result["success"] is True
        quality_report = result["data"]["quality_report"]
        
        assert "overall_quality" in quality_report
        assert "flight_quality_scores" in quality_report
        assert "quality_issues" in quality_report
        assert "recommendations" in quality_report
        
        # 质量分数应该较低
        assert quality_report["overall_quality"] < 0.8
        assert len(quality_report["quality_issues"]) > 0
        assert len(quality_report["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_invalid_input(self):
        """测试无效输入。"""
        # 空航线配置
        arguments = {
            "flight_configurations": []
        }
        
        result = await self.coordinator.execute(arguments)
        
        assert result["success"] is False
        assert "输入参数无效" in result["error"]
    
    @pytest.mark.asyncio
    async def test_malformed_flight_path(self):
        """测试格式错误的航线路径。"""
        malformed_configs = [
            {
                "flight_id": "malformed_flight",
                "flight_path": {
                    # 缺少waypoints
                    "global_speed": 5.0,
                    "global_height": 100.0
                }
            }
        ]
        
        arguments = {
            "flight_configurations": malformed_configs
        }
        
        result = await self.coordinator.execute(arguments)
        
        assert result["success"] is False
        assert "多航线协调失败" in result["error"]
    
    def test_parse_flight_configurations(self):
        """测试航线配置解析。"""
        parsed_configs = self.coordinator._parse_flight_configurations(self.test_flight_configs)
        
        assert len(parsed_configs) == 2
        assert all(isinstance(config, FlightConfiguration) for config in parsed_configs)
        assert parsed_configs[0].flight_id == "flight_nadir"
        assert parsed_configs[1].flight_id == "flight_oblique"
        assert parsed_configs[0].priority == FlightPriority.HIGH
        assert parsed_configs[1].priority == FlightPriority.MEDIUM
    
    def test_calculate_compatibility_score(self):
        """测试兼容性分数计算。"""
        # 创建两个测试配置
        waypoints = [
            Waypoint(
                index=0,
                coordinates=Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0),
                speed=5.0
            )
        ]
        
        flight_path = FlightPath(
            waypoints=waypoints,
            global_speed=5.0,
            global_height=100.0,
            height_mode=HeightMode.EGM96
        )
        
        config1 = FlightConfiguration(
            flight_id="config1",
            flight_path=flight_path,
            priority=FlightPriority.HIGH,
            estimated_duration=10.0,
            battery_consumption=25.0,
            photo_count=50,
            coverage_area=5.0,
            gimbal_angles={"pitch": -90.0, "yaw": 0.0},
            metadata={}
        )
        
        config2 = FlightConfiguration(
            flight_id="config2",
            flight_path=flight_path,
            priority=FlightPriority.HIGH,
            estimated_duration=10.0,
            battery_consumption=25.0,
            photo_count=50,
            coverage_area=5.0,
            gimbal_angles={"pitch": -90.0, "yaw": 0.0},  # 相同角度
            metadata={}
        )
        
        # 相同配置应该有高兼容性
        score = self.coordinator._calculate_compatibility_score(config1, config2)
        assert score > 0.5
        
        # 修改config2的云台角度
        config2.gimbal_angles = {"pitch": -45.0, "yaw": 90.0}
        score_different = self.coordinator._calculate_compatibility_score(config1, config2)
        assert score_different < score  # 兼容性应该降低
    
    def test_calculate_flight_statistics(self):
        """测试航线统计计算。"""
        waypoints = [
            Waypoint(
                index=0,
                coordinates=Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0),
                speed=5.0
            ),
            Waypoint(
                index=1,
                coordinates=Coordinates(latitude=40.7228, longitude=-74.0060, altitude=100.0),
                speed=5.0
            )
        ]
        
        flight_path = FlightPath(
            waypoints=waypoints,
            global_speed=5.0,
            global_height=100.0,
            height_mode=HeightMode.EGM96
        )
        
        config = {"flight_speed": 5.0, "photo_interval": 2.0}
        
        stats = self.coordinator._calculate_flight_statistics(flight_path, config)
        
        assert "duration" in stats
        assert "battery_consumption" in stats
        assert "photo_count" in stats
        assert "coverage_area" in stats
        assert "total_distance" in stats
        
        assert stats["duration"] > 0
        assert stats["battery_consumption"] > 0
        assert stats["photo_count"] >= 0
        assert stats["coverage_area"] >= 0
        assert stats["total_distance"] > 0
    
    def test_optimize_flight_sequence(self):
        """测试航线顺序优化。"""
        # 创建测试配置
        waypoints = [
            Waypoint(
                index=0,
                coordinates=Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0),
                speed=5.0
            )
        ]
        
        flight_path = FlightPath(
            waypoints=waypoints,
            global_speed=5.0,
            global_height=100.0,
            height_mode=HeightMode.EGM96
        )
        
        configs = [
            FlightConfiguration(
                flight_id="low_priority",
                flight_path=flight_path,
                priority=FlightPriority.LOW,
                estimated_duration=10.0,
                battery_consumption=25.0,
                photo_count=50,
                coverage_area=5.0,
                gimbal_angles={"pitch": -90.0, "yaw": 0.0},
                metadata={}
            ),
            FlightConfiguration(
                flight_id="high_priority",
                flight_path=flight_path,
                priority=FlightPriority.HIGH,
                estimated_duration=10.0,
                battery_consumption=25.0,
                photo_count=50,
                coverage_area=5.0,
                gimbal_angles={"pitch": -90.0, "yaw": 0.0},
                metadata={}
            )
        ]
        
        # 测试顺序模式
        sequential = self.coordinator._optimize_flight_sequence(
            configs, FlightSequenceMode.SEQUENTIAL, 25.0, 20.0
        )
        # 高优先级应该在前面
        assert sequential[0].priority == FlightPriority.HIGH
        
        # 测试并行模式
        parallel = self.coordinator._optimize_flight_sequence(
            configs, FlightSequenceMode.PARALLEL, 25.0, 20.0
        )
        assert len(parallel) == 2
        
        # 测试优化模式
        optimized = self.coordinator._optimize_flight_sequence(
            configs, FlightSequenceMode.OPTIMIZED, 25.0, 20.0
        )
        assert len(optimized) == 2
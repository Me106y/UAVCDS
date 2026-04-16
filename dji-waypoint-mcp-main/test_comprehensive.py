#!/usr/bin/env python3
"""
大疆航线规划MCP服务 - 全面测试脚本
测试所有模块的基本功能和集成
"""

import sys
import asyncio
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, List

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComprehensiveTest:
    """全面测试类"""
    
    def __init__(self):
        self.test_results = {}
        self.failed_tests = []
        
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始全面测试大疆航线规划MCP服务")
        
        # 测试模块导入
        await self.test_imports()
        
        # 测试数据模型
        await self.test_models()
        
        # 测试工具注册
        await self.test_tool_registry()
        
        # 测试各个MCP工具
        await self.test_mcp_tools()
        
        # 测试辅助模块
        await self.test_utils()
        
        # 生成测试报告
        self.generate_report()
    
    async def test_imports(self):
        """测试模块导入"""
        logger.info("📦 测试模块导入...")
        
        test_cases = [
            ("配置模块", "dji_waypoint_mcp.config"),
            ("服务器模块", "dji_waypoint_mcp.server"),
            ("数据模型", "dji_waypoint_mcp.models"),
            ("工具注册", "dji_waypoint_mcp.tools.registry"),
            ("基础工具", "dji_waypoint_mcp.tools.base"),
            ("航点规划", "dji_waypoint_mcp.tools.waypoint_planning"),
            ("建图航拍", "dji_waypoint_mcp.tools.mapping_missions"),
            ("倾斜摄影", "dji_waypoint_mcp.tools.oblique_missions"),
            ("航带飞行", "dji_waypoint_mcp.tools.strip_missions"),
            ("路径优化", "dji_waypoint_mcp.tools.route_optimizer"),
            ("多航线协调", "dji_waypoint_mcp.tools.multi_flight_coordinator"),
            ("设备查询", "dji_waypoint_mcp.tools.device_query"),
            ("验证工具", "dji_waypoint_mcp.tools.validation"),
            ("辅助工具", "dji_waypoint_mcp.tools.utility_tools"),
            ("KMZ生成", "dji_waypoint_mcp.tools.kmz_generation"),
            ("设备数据库", "dji_waypoint_mcp.data.aircraft_database"),
            ("几何计算", "dji_waypoint_mcp.utils.geometry"),
            ("坐标转换", "dji_waypoint_mcp.utils.coordinate_transforms"),
            ("覆盖分析", "dji_waypoint_mcp.utils.coverage_analysis"),
            ("兼容性检查", "dji_waypoint_mcp.utils.compatibility_checker"),
        ]
        
        import_results = {}
        
        for name, module_name in test_cases:
            try:
                __import__(module_name)
                import_results[name] = "✅ 成功"
                logger.info(f"  ✅ {name}: 导入成功")
            except Exception as e:
                import_results[name] = f"❌ 失败: {str(e)}"
                logger.error(f"  ❌ {name}: 导入失败 - {str(e)}")
                self.failed_tests.append(f"导入{name}")
        
        self.test_results["模块导入"] = import_results
    
    async def test_models(self):
        """测试数据模型"""
        logger.info("🏗️ 测试数据模型...")
        
        model_results = {}
        
        try:
            from dji_waypoint_mcp.models import (
                Coordinates, Waypoint, FlightPath, 
                AircraftModel, PayloadModel
            )
            
            # 测试坐标模型
            try:
                coords = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
                assert coords.latitude == 40.7128
                assert coords.longitude == -74.0060
                assert coords.altitude == 100.0
                model_results["坐标模型"] = "✅ 成功"
                logger.info("  ✅ 坐标模型: 测试通过")
            except Exception as e:
                model_results["坐标模型"] = f"❌ 失败: {str(e)}"
                logger.error(f"  ❌ 坐标模型: {str(e)}")
                self.failed_tests.append("坐标模型")
            
            # 测试航点模型
            try:
                waypoint = Waypoint(
                    index=0,
                    coordinates=coords,
                    speed=5.0
                )
                assert waypoint.index == 0
                assert waypoint.coordinates.latitude == 40.7128
                model_results["航点模型"] = "✅ 成功"
                logger.info("  ✅ 航点模型: 测试通过")
            except Exception as e:
                model_results["航点模型"] = f"❌ 失败: {str(e)}"
                logger.error(f"  ❌ 航点模型: {str(e)}")
                self.failed_tests.append("航点模型")
            
            # 测试航线模型
            try:
                coords2 = Coordinates(latitude=40.7228, longitude=-74.0060, altitude=100.0)
                waypoint2 = Waypoint(index=1, coordinates=coords2, speed=5.0)
                
                flight_path = FlightPath(
                    waypoints=[waypoint, waypoint2],
                    global_speed=5.0
                )
                assert len(flight_path.waypoints) == 2
                model_results["航线模型"] = "✅ 成功"
                logger.info("  ✅ 航线模型: 测试通过")
            except Exception as e:
                model_results["航线模型"] = f"❌ 失败: {str(e)}"
                logger.error(f"  ❌ 航线模型: {str(e)}")
                self.failed_tests.append("航线模型")
                
        except Exception as e:
            model_results["模型导入"] = f"❌ 失败: {str(e)}"
            logger.error(f"  ❌ 模型导入失败: {str(e)}")
            self.failed_tests.append("模型导入")
        
        self.test_results["数据模型"] = model_results
    
    async def test_tool_registry(self):
        """测试工具注册"""
        logger.info("🔧 测试工具注册...")
        
        registry_results = {}
        
        try:
            from dji_waypoint_mcp.tools.registry import ToolRegistry
            from dji_waypoint_mcp.tools.waypoint_planning import WaypointPlanningTool
            
            # 创建注册表
            registry = ToolRegistry()
            
            # 注册工具
            tool = WaypointPlanningTool()
            registry.register_tool(tool)
            
            # 检查注册结果
            tools = registry.get_all_tools()
            assert len(tools) > 0
            
            tool_names = registry.get_tool_names()
            assert "plan_waypoint_mission" in tool_names
            
            registry_results["工具注册"] = "✅ 成功"
            logger.info("  ✅ 工具注册: 测试通过")
            
        except Exception as e:
            registry_results["工具注册"] = f"❌ 失败: {str(e)}"
            logger.error(f"  ❌ 工具注册: {str(e)}")
            self.failed_tests.append("工具注册")
        
        self.test_results["工具注册"] = registry_results
    
    async def test_mcp_tools(self):
        """测试MCP工具"""
        logger.info("🛠️ 测试MCP工具...")
        
        tools_results = {}
        
        # 测试工具列表
        tool_classes = [
            ("航点规划工具", "dji_waypoint_mcp.tools.waypoint_planning", "WaypointPlanningTool"),
            ("建图航拍工具", "dji_waypoint_mcp.tools.mapping_missions", "MappingMissionTool"),
            ("倾斜摄影工具", "dji_waypoint_mcp.tools.oblique_missions", "ObliqueMissionTool"),
            ("航带飞行工具", "dji_waypoint_mcp.tools.strip_missions", "StripMissionTool"),
            ("路径优化工具", "dji_waypoint_mcp.tools.route_optimizer", "RouteOptimizer"),
            ("多航线协调工具", "dji_waypoint_mcp.tools.multi_flight_coordinator", "MultiFlightCoordinator"),
            ("设备查询工具", "dji_waypoint_mcp.tools.device_query", "DeviceQueryTool"),
            ("验证工具", "dji_waypoint_mcp.tools.validation", "ValidationTool"),
            ("辅助工具", "dji_waypoint_mcp.tools.utility_tools", "UtilityTools"),
            ("KMZ生成工具", "dji_waypoint_mcp.tools.kmz_generation", "KMZGenerationTool"),
        ]
        
        for tool_name, module_name, class_name in tool_classes:
            try:
                # 导入模块
                module = __import__(module_name, fromlist=[class_name])
                tool_class = getattr(module, class_name)
                
                # 创建工具实例
                tool = tool_class()
                
                # 获取工具定义
                tool_def = tool.get_tool_definition()
                assert tool_def.name is not None
                assert tool_def.description is not None
                
                tools_results[tool_name] = "✅ 成功"
                logger.info(f"  ✅ {tool_name}: 测试通过")
                
            except Exception as e:
                tools_results[tool_name] = f"❌ 失败: {str(e)}"
                logger.error(f"  ❌ {tool_name}: {str(e)}")
                self.failed_tests.append(tool_name)
        
        self.test_results["MCP工具"] = tools_results
    
    async def test_utils(self):
        """测试辅助模块"""
        logger.info("🔧 测试辅助模块...")
        
        utils_results = {}
        
        # 测试几何计算
        try:
            from dji_waypoint_mcp.utils.geometry import geometry_calculator
            from dji_waypoint_mcp.models import Coordinates
            
            coord1 = Coordinates(latitude=40.7128, longitude=-74.0060)
            coord2 = Coordinates(latitude=40.7228, longitude=-74.0060)
            
            distance = geometry_calculator.haversine_distance(coord1, coord2)
            assert distance > 0
            
            utils_results["几何计算"] = "✅ 成功"
            logger.info("  ✅ 几何计算: 测试通过")
            
        except Exception as e:
            utils_results["几何计算"] = f"❌ 失败: {str(e)}"
            logger.error(f"  ❌ 几何计算: {str(e)}")
            self.failed_tests.append("几何计算")
        
        # 测试坐标转换
        try:
            from dji_waypoint_mcp.utils.coordinate_transforms import coordinate_transformer
            
            # 简单的坐标转换测试（使用中国境内坐标）
            lat, lon = 39.9042, 116.4074  # 北京坐标
            gcj_lat, gcj_lon = coordinate_transformer.wgs84_to_gcj02(lat, lon)
            
            # 检查转换结果不同（中国境内坐标应该有偏移）
            assert abs(gcj_lat - lat) > 0.0001 or abs(gcj_lon - lon) > 0.0001
            
            utils_results["坐标转换"] = "✅ 成功"
            logger.info("  ✅ 坐标转换: 测试通过")
            
        except Exception as e:
            utils_results["坐标转换"] = f"❌ 失败: {str(e)}"
            logger.error(f"  ❌ 坐标转换: {str(e)}")
            self.failed_tests.append("坐标转换")
        
        # 测试设备数据库
        try:
            from dji_waypoint_mcp.data.aircraft_database import aircraft_database
            
            # 获取设备信息
            aircraft_specs = aircraft_database.get_aircraft_specs("M30")
            assert aircraft_specs is not None
            assert aircraft_specs.model_name == "Matrice 30"
            
            all_aircraft = aircraft_database.get_all_aircraft()
            assert len(all_aircraft) > 0
            
            utils_results["设备数据库"] = "✅ 成功"
            logger.info("  ✅ 设备数据库: 测试通过")
            
        except Exception as e:
            utils_results["设备数据库"] = f"❌ 失败: {str(e)}"
            logger.error(f"  ❌ 设备数据库: {str(e)}")
            self.failed_tests.append("设备数据库")
        
        self.test_results["辅助模块"] = utils_results
    
    def generate_report(self):
        """生成测试报告"""
        logger.info("📊 生成测试报告...")
        
        total_tests = sum(len(results) for results in self.test_results.values())
        failed_count = len(self.failed_tests)
        success_count = total_tests - failed_count
        
        print("\\n" + "="*80)
        print("🎯 大疆航线规划MCP服务 - 全面测试报告")
        print("="*80)
        
        print(f"\\n📈 总体统计:")
        print(f"  总测试数: {total_tests}")
        print(f"  成功数: {success_count}")
        print(f"  失败数: {failed_count}")
        print(f"  成功率: {success_count/total_tests*100:.1f}%")
        
        print(f"\\n📋 详细结果:")
        for category, results in self.test_results.items():
            print(f"\\n  {category}:")
            for test_name, result in results.items():
                print(f"    {test_name}: {result}")
        
        if self.failed_tests:
            print(f"\\n❌ 失败的测试:")
            for failed_test in self.failed_tests:
                print(f"    - {failed_test}")
        else:
            print(f"\\n🎉 所有测试都通过了！")
        
        print("\\n" + "="*80)
        
        # 保存报告到文件
        report_file = Path("test_report.md")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 大疆航线规划MCP服务 - 测试报告\\n\\n")
            f.write(f"## 总体统计\\n\\n")
            f.write(f"- 总测试数: {total_tests}\\n")
            f.write(f"- 成功数: {success_count}\\n")
            f.write(f"- 失败数: {failed_count}\\n")
            f.write(f"- 成功率: {success_count/total_tests*100:.1f}%\\n\\n")
            
            f.write("## 详细结果\\n\\n")
            for category, results in self.test_results.items():
                f.write(f"### {category}\\n\\n")
                for test_name, result in results.items():
                    status = "✅" if "成功" in result else "❌"
                    f.write(f"- {status} {test_name}: {result}\\n")
                f.write("\\n")
            
            if self.failed_tests:
                f.write("## 失败的测试\\n\\n")
                for failed_test in self.failed_tests:
                    f.write(f"- {failed_test}\\n")
        
        logger.info(f"📄 测试报告已保存到: {report_file}")


async def main():
    """主函数"""
    try:
        tester = ComprehensiveTest()
        await tester.run_all_tests()
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
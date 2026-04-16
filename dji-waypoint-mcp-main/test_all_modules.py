#!/usr/bin/env python3
"""
全面测试脚本 - 检查所有模块的基本功能
"""

import sys
import os
import asyncio
import traceback
from pathlib import Path

# 添加src到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """测试所有模块的导入"""
    print("🔍 测试模块导入...")
    
    try:
        # 测试核心模块
        from dji_waypoint_mcp import __version__
        print(f"✅ 核心模块导入成功，版本: {__version__}")
        
        # 测试配置
        from dji_waypoint_mcp.config import settings
        print(f"✅ 配置模块导入成功，服务器名: {settings.server_name}")
        
        # 测试数据模型
        from dji_waypoint_mcp.models import (
            Coordinates, Waypoint, FlightPath, 
            AircraftModel, PayloadModel
        )
        print("✅ 数据模型导入成功")
        
        # 测试工具模块
        from dji_waypoint_mcp.tools import (
            WaypointPlanningTool, MappingMissionTool, 
            ObliqueMissionTool, ValidationTool
        )
        print("✅ 工具模块导入成功")
        
        # 测试工具类
        from dji_waypoint_mcp.utils.geometry import geometry_calculator
        from dji_waypoint_mcp.utils.coordinate_transforms import coordinate_transformer
        print("✅ 工具类导入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        traceback.print_exc()
        return False

def test_data_models():
    """测试数据模型"""
    print("\n🔍 测试数据模型...")
    
    try:
        from dji_waypoint_mcp.models import Coordinates, Waypoint, FlightPath
        
        # 测试坐标
        coord1 = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        coord2 = Coordinates(latitude=40.7228, longitude=-74.0060, altitude=100.0)
        print(f"✅ 坐标创建成功: {coord1}")
        
        # 测试航点
        wp1 = Waypoint(index=0, coordinates=coord1)
        wp2 = Waypoint(index=1, coordinates=coord2)
        print(f"✅ 航点创建成功: {wp1.index}")
        
        # 测试航线
        flight_path = FlightPath(waypoints=[wp1, wp2])
        print(f"✅ 航线创建成功，航点数: {len(flight_path.waypoints)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据模型测试失败: {e}")
        traceback.print_exc()
        return False

def test_geometry_utils():
    """测试几何工具"""
    print("\n🔍 测试几何工具...")
    
    try:
        from dji_waypoint_mcp.utils.geometry import geometry_calculator
        from dji_waypoint_mcp.models import Coordinates
        
        coord1 = Coordinates(latitude=40.7128, longitude=-74.0060)
        coord2 = Coordinates(latitude=40.7228, longitude=-74.0060)
        
        # 测试距离计算
        distance = geometry_calculator.haversine_distance(coord1, coord2)
        print(f"✅ 距离计算成功: {distance:.2f}m")
        
        # 测试方位角计算
        bearing = geometry_calculator.calculate_bearing(coord1, coord2)
        print(f"✅ 方位角计算成功: {bearing:.2f}°")
        
        return True
        
    except Exception as e:
        print(f"❌ 几何工具测试失败: {e}")
        traceback.print_exc()
        return False

async def test_mcp_tools():
    """测试MCP工具"""
    print("\n🔍 测试MCP工具...")
    
    try:
        from dji_waypoint_mcp.tools.waypoint_planning import WaypointPlanningTool
        from dji_waypoint_mcp.tools.mapping_missions import MappingMissionTool
        from dji_waypoint_mcp.tools.validation import ValidationTool
        
        # 测试航点规划工具
        waypoint_tool = WaypointPlanningTool()
        tool_def = waypoint_tool.get_tool_definition()
        print(f"✅ 航点规划工具: {tool_def.name}")
        
        # 测试建图工具
        mapping_tool = MappingMissionTool()
        tool_def = mapping_tool.get_tool_definition()
        print(f"✅ 建图工具: {tool_def.name}")
        
        # 测试验证工具
        validation_tool = ValidationTool()
        tool_def = validation_tool.get_tool_definition()
        print(f"✅ 验证工具: {tool_def.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP工具测试失败: {e}")
        traceback.print_exc()
        return False

def test_device_database():
    """测试设备数据库"""
    print("\n🔍 测试设备数据库...")
    
    try:
        from dji_waypoint_mcp.data.aircraft_database import aircraft_database
        
        # 测试获取设备信息
        m30_specs = aircraft_database.get_aircraft_specs("M30")
        if m30_specs:
            print(f"✅ M30设备信息: {m30_specs.model_name}")
        else:
            print("❌ 未找到M30设备信息")
            return False
        
        # 测试获取所有设备
        all_aircraft = aircraft_database.get_all_aircraft()
        print(f"✅ 设备数据库包含 {len(all_aircraft)} 个设备")
        
        return True
        
    except Exception as e:
        print(f"❌ 设备数据库测试失败: {e}")
        traceback.print_exc()
        return False

async def test_server_initialization():
    """测试服务器初始化"""
    print("\n🔍 测试服务器初始化...")
    
    try:
        from dji_waypoint_mcp.server import DJIWaypointMCPServer
        
        # 创建服务器实例
        server = DJIWaypointMCPServer()
        print("✅ 服务器实例创建成功")
        
        # 检查工具注册
        tools = server.tool_registry.get_all_tools()
        print(f"✅ 已注册 {len(tools)} 个MCP工具")
        
        # 列出所有工具
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")
        
        return True
        
    except Exception as e:
        print(f"❌ 服务器初始化测试失败: {e}")
        traceback.print_exc()
        return False

def test_coordinate_transforms():
    """测试坐标转换"""
    print("\n🔍 测试坐标转换...")
    
    try:
        from dji_waypoint_mcp.utils.coordinate_transforms import coordinate_transformer
        
        # 测试WGS84到GCJ02转换
        wgs_lat, wgs_lon = 40.7128, -74.0060
        gcj_lat, gcj_lon = coordinate_transformer.wgs84_to_gcj02(wgs_lat, wgs_lon)
        print(f"✅ WGS84到GCJ02转换: ({wgs_lat}, {wgs_lon}) -> ({gcj_lat:.6f}, {gcj_lon:.6f})")
        
        return True
        
    except Exception as e:
        print(f"❌ 坐标转换测试失败: {e}")
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🚀 开始全面测试大疆航线规划MCP服务")
    print("=" * 60)
    
    test_results = []
    
    # 运行所有测试
    test_results.append(("模块导入", test_imports()))
    test_results.append(("数据模型", test_data_models()))
    test_results.append(("几何工具", test_geometry_utils()))
    test_results.append(("MCP工具", await test_mcp_tools()))
    test_results.append(("设备数据库", test_device_database()))
    test_results.append(("服务器初始化", await test_server_initialization()))
    test_results.append(("坐标转换", test_coordinate_transforms()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 个测试通过, {failed} 个测试失败")
    
    if failed == 0:
        print("🎉 所有测试都通过了！系统运行正常。")
        return True
    else:
        print("⚠️  有测试失败，需要修复问题。")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
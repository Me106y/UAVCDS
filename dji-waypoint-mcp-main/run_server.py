#!/usr/bin/env python3
"""
大疆航线规划MCP服务启动脚本
"""

import sys
import asyncio
import logging
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.dji_waypoint_mcp.server import main

if __name__ == "__main__":
    print("🚀 启动大疆航线规划MCP服务...")
    print("📡 服务将在stdio模式下运行，等待MCP客户端连接")
    print("🔧 支持的工具:")
    print("   - plan_waypoint_mission: 航点飞行规划")
    print("   - plan_mapping_mission: 建图航拍规划") 
    print("   - plan_oblique_mission: 倾斜摄影规划")
    print("   - plan_strip_mission: 航带飞行规划")
    print("   - optimize_route: 路径优化")
    print("   - coordinate_multi_flights: 多航线协调")
    print("   - query_device_info: 设备信息查询")
    print("   - validate_mission_compatibility: 兼容性验证")
    print("   - utility_functions: 辅助功能")
    print("   - generate_kmz: KMZ文件生成")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")
        sys.exit(1)
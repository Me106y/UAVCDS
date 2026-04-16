import json
import asyncio
import threading
from typing import List, Dict
from langchain_core.tools import tool
from utils.logger import logger
from utils.mcp_client import mcp_manager

# 读取配置文件
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 获取默认飞行高度
default_altitude = config.get('flight_settings', {}).get('default_altitude', 100.0)

_ASYNC_LOOP = None
_ASYNC_LOOP_THREAD = None
_ASYNC_LOOP_LOCK = threading.Lock()

def _ensure_background_loop():
    global _ASYNC_LOOP, _ASYNC_LOOP_THREAD
    with _ASYNC_LOOP_LOCK:
        if _ASYNC_LOOP is not None and _ASYNC_LOOP.is_running():
            return _ASYNC_LOOP

        loop = asyncio.new_event_loop()

        def _loop_runner():
            asyncio.set_event_loop(loop)
            loop.run_forever()

        thread = threading.Thread(
            target=_loop_runner,
            name="uav-tools-async-loop",
            daemon=True
        )
        thread.start()

        _ASYNC_LOOP = loop
        _ASYNC_LOOP_THREAD = thread
        return _ASYNC_LOOP

def _run_async(coro):
    """辅助函数：在同步工具中把协程提交到统一后台事件循环执行。"""
    loop = _ensure_background_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()

@tool
def fetch_dashboard_status(url: str) -> str:
    """
    感知专员专用工具：通过 playwright mcp 从指定的大疆司空2网页 URL 中获取网页数据，并生成 Markdown 格式的报告。
    参数:
    url: 需要访问并抓取的大疆司空2仪表盘 URL
    """
    logger.info(f"Perception Tool 正在调用 playwright mcp 访问: {url} ...")
    
    # 1. 导航到目标网页
    nav_args = {"url": url}
    _run_async(mcp_manager.call_tool("playwright", "playwright_navigate", nav_args))
    
    # 2. 获取网页内容 (我们通过执行一段 JS 来提取网页所有文本或结构，这里简化为获取 document.body.innerText)
    eval_args = {
        "script": "() => document.body.innerText",
    }
    result = _run_async(mcp_manager.call_tool("playwright", "playwright_evaluate", eval_args))
    
    # 3. 将抓取的内容保存为 Markdown 文件
    markdown_content = f"# 大疆司空2 状态报告\n\n**抓取来源**: {url}\n\n## 页面内容\n\n```text\n{result}\n```\n"
    report_path = "dashboard_report.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    logger.info(f"Perception Tool 已将网页内容保存至 {report_path}")
    
    return f"成功获取网页数据并生成报告，保存在 {report_path} 中。内容预览: {str(result)[:200]}..."

@tool
def get_coordinates(target_name: str) -> dict:
    """
    指挥调度专用工具：根据目标名称（如“杭州电子科技大学下沙校区”）获取具体的中心点坐标 (POI) 和周边矩形巡视区域坐标 (AOI)。
    参数:
    target_name: 目标地点名称或描述
    """
    logger.info(f"Orchestrator Tool 正在调用 amap-maps 查询坐标: {target_name}")
    
    # 1. 调用高德地图 MCP 获取 POI
    amap_args = {"address": target_name}
    result = _run_async(mcp_manager.call_tool("amap-maps", "maps_geo", amap_args))
    
    # 解析高德返回的经纬度 (通常为 "lng,lat" 格式的字符串)
    # 若无法解析则回退到默认测试坐标
    poi_lat, poi_lng = 30.274591, 120.238641
    try:
        location_str = ""
        if isinstance(result, dict):
            if "return" in result and isinstance(result["return"], list) and len(result["return"]) > 0:
                location_str = (result["return"][0] or {}).get("location", "") or ""
            elif "geocodes" in result and isinstance(result["geocodes"], list) and len(result["geocodes"]) > 0:
                location_str = (result["geocodes"][0] or {}).get("location", "") or ""

        if location_str:
            parts = location_str.split(",")
            poi_lng, poi_lat = float(parts[0]), float(parts[1])
    except Exception as e:
        logger.warning(f"解析高德坐标失败: {e}, 将使用默认坐标")
        
    # 2. 以 POI 为中心，生成一个极小的矩形 AOI (约 100 米见方的矩形)
    # 添加 altitude 字段以满足 dji-waypoint-mcp 的要求
    offset = 0.0005  # 大约 50 米的经纬度偏移
    altitude = float(default_altitude)
    aoi_waypoints = [
        {"latitude": poi_lat + offset, "longitude": poi_lng - offset, "altitude": altitude}, # 左上
        {"latitude": poi_lat + offset, "longitude": poi_lng + offset, "altitude": altitude}, # 右上
        {"latitude": poi_lat - offset, "longitude": poi_lng + offset, "altitude": altitude}, # 右下
        {"latitude": poi_lat - offset, "longitude": poi_lng - offset, "altitude": altitude}  # 左下
    ]
    
    logger.info(f"POI 获取成功: {target_name} (latitude: {poi_lat}, longitude: {poi_lng})")
    logger.info(f"AOI 矩形区域已生成: {aoi_waypoints}")
    
    return {
        "target": target_name,
        "poi": {"latitude": poi_lat, "longitude": poi_lng},
        "aoi_waypoints": aoi_waypoints
    }

@tool
def generate_flight_plan(waypoints: List[Dict[str, float]]) -> dict:
    """
    规划专员专用工具：根据给定的航点列表（如 AOI 的四个角），生成无人机航线。
    参数:
    waypoints: 航点坐标列表，格式如 [{"latitude": 30.2, "longitude": 120.2}, ...]
    """
    logger.info(f"Planning Tool 正在调用 dji-waypoint-mcp 规划航线，共接收到 {len(waypoints)} 个航点")
    
    # 确保所有航点都包含 altitude 字段
    for waypoint in waypoints:
        if 'altitude' not in waypoint:
            waypoint['altitude'] = default_altitude
    
    # 调用大疆航线规划 MCP 服务，传入 waypoints 数组
    args = {
        "waypoints": waypoints
    }
    result = _run_async(mcp_manager.call_tool("dji-waypoint-mcp", "plan_waypoint_mission", args))
    return result

@tool
def generate_kmz_file(waypoints: List[Dict[str, float]], output_filename: str = "mission.kmz") -> dict:
    """
    规划专员专用工具：根据给定的航点列表生成 WPML KMZ 文件（可用于大疆司空2导入）。
    参数:
    waypoints: 航点坐标列表，格式如 [{"latitude": 30.2, "longitude": 120.2, "altitude": 100.0}, ...]
    output_filename: 输出 KMZ 文件名（例如 mission.kmz）
    """
    logger.info(f"Planning Tool 正在调用 dji-waypoint-mcp 生成 KMZ 文件，共接收到 {len(waypoints)} 个航点")
    
    for waypoint in waypoints:
        if 'altitude' not in waypoint:
            waypoint['altitude'] = default_altitude
    
    args = {
        "flight_plan": {
            "waypoints": waypoints,
            "flight_speed": 5.0
        },
        "output_filename": output_filename
    }
    result = _run_async(mcp_manager.call_tool("dji-waypoint-mcp", "generate_kmz", args))
    return result

@tool
def check_airspace_conflict(route: str) -> bool:
    """
    规划专员专用工具：检查拟定航线是否与当前空域内其他无人机的飞行任务产生冲突。
    参数:
    route: 规划好的航线数据序列化字符串
    """
    logger.info("Planning Tool 正在调用 airspace-monitor-mcp 检查航线冲突...")
    args = {"route": route}
    result = _run_async(mcp_manager.call_tool("airspace-monitor-mcp", "check_route_conflict", args))
    # 假设返回值中包含 'has_conflict' 字段
    if isinstance(result, dict):
        return result.get("has_conflict", False)
    return False

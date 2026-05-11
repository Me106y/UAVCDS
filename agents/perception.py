from utils.logger import logger
from tools.uav_tools import fetch_dashboard_status, get_coordinates

class PerceptionAgent:
    """
    感知专员 (Perception Agent)
    职责：负责“观察”世界，利用Playwright MCP定时“看”司空2的屏幕。
    关键点：不负责决策，只负责将非结构化数据转化为结构化文本报告给指挥官。
    """
    def __init__(self, mcp_settings):
        self.mcp_settings = mcp_settings
        logger.info("Perception Agent 初始化完成，准备挂载 Playwright MCP")
        
    def fetch_dashboard_status(self):
        """
        Action: fetch_dashboard
        """
        logger.info("Perception Agent 正在获取大疆司空2仪表盘状态...")
        url = (self.mcp_settings or {}).get("dji", {}).get("url", "")
        if not url:
            return {"error": "未配置 dji.url，无法读取司空2仪表盘"}
        return fetch_dashboard_status.invoke({"url": url})

    def get_coordinates(self, target_name: str) -> dict:
        logger.info(f"Perception Agent 正在获取地点 POI/AOI: {target_name}")
        return get_coordinates.invoke({"target_name": target_name})

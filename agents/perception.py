from utils.logger import logger

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
        # TODO: 通过 playwright-mcp-server 获取网页数据，利用VLM识别画面提取结构化数据
        return {
            "drone_a": {"status": "working", "remaining_time": 20, "battery": 45},
            "drone_b": {"status": "idle", "battery": 98}
        }

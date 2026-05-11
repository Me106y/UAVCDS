from utils.logger import logger
from tools.uav_tools import generate_flight_plan, generate_kmz_file, check_airspace_conflict

class PlanningAgent:
    """
    规划专员 (Planning Agent)
    职责：负责数学计算，利用航迹规划MCP，计算两点之间是否安全、电量是否够用、航线如何生成。
    """
    def __init__(self, mcp_settings):
        self.mcp_settings = mcp_settings
        self.last_planned_waypoints = []  # 记录最近一次规划的详细航点
        logger.info("Planning Agent 初始化完成，准备挂载 dji-waypoint-mcp")
        
    def generate_flight_plan(self, waypoints):
        logger.info(f"Planning Agent 正在规划航线，共 {len(waypoints)} 个航点")
        result = generate_flight_plan.invoke({"waypoints": waypoints})
        
        # 记录规划后的详细航点，供后续 KMZ 生成使用
        if isinstance(result, dict):
            data = result.get("data") or {}
            flight_path = data.get("flight_path") or {}
            planned_points = flight_path.get("waypoints") or []
            if planned_points:
                self.last_planned_waypoints = planned_points
                logger.info(f"Planning Agent 已记录规划后的详细航点: {len(self.last_planned_waypoints)} 个")
        
        return result
        
    def generate_kmz(self, waypoints=None, output_filename: str = "mission.kmz"):
        """
        生成 KMZ。如果未提供 waypoints，则使用最近一次规划的结果。
        """
        target_waypoints = waypoints
        if not target_waypoints or len(target_waypoints) <= 4:
            if self.last_planned_waypoints:
                target_waypoints = self.last_planned_waypoints
                logger.info(f"Planning Agent: 未提供详细航点，将使用最近规划的 {len(target_waypoints)} 个航点生成 KMZ")
            else:
                logger.warning("Planning Agent: 未找到已规划的航点，将使用输入的原始航点")
                target_waypoints = waypoints or []

        output_filename = "mission.kmz"
        logger.info(f"Planning Agent 正在生成 KMZ 文件: {output_filename}，航点数: {len(target_waypoints)}")
        return generate_kmz_file.invoke({"waypoints": target_waypoints, "output_filename": output_filename})

    def check_airspace_conflict(self, route: str) -> bool:
        # 该功能暂时停用
        return False

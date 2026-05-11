import os
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from utils.logger import logger
from agents.perception import PerceptionAgent
from agents.planning import PlanningAgent
from agents.prompt_optimizer import PromptOptimizerAgent

class OrchestratorAgent:
    """
    总指挥官 (Orchestrator Agent)
    使用 LangGraph 标准 create_react_agent 框架与模型，自动选择工具解决调度需求。
    """
    def __init__(self, config):
        self.config = config
        self._history: list[tuple[str, str]] = []
        self._history_max_pairs = 8
        self.prompt_optimizer = PromptOptimizerAgent(self.config)
        self.perception_agent = PerceptionAgent(self.config)
        self.planning_agent = PlanningAgent(self.config)
        
        # 配置通义千问模型
        os.environ["DASHSCOPE_API_KEY"] = self.config["api_keys"]["dashscope"]
        self.llm = ChatOpenAI(
            api_key=os.environ["DASHSCOPE_API_KEY"],
            base_url="https://api.xiaomimimo.com/v1",
            model=self.config["models"]["chat"],
            temperature=0.2,
            model_kwargs={"parallel_tool_calls": False}
        )

        # 定义工具集
        self.tools = [
            StructuredTool.from_function(
                func=self.perception_agent.get_coordinates,
                name="get_coordinates",
                description="获取目标地点的经纬度坐标（POI）及矩形AOI航点。输入参数为 target_name（地点名称）。"
            ),
            StructuredTool.from_function(
                func=self.perception_agent.fetch_dashboard_status,
                name="fetch_dashboard_status",
                description="读取大疆司空2仪表盘状态，获取无人机实时飞行信息。"
            ),
            StructuredTool.from_function(
                func=self.generate_flight_plan_wrapper,
                name="generate_flight_plan",
                description="根据航点规划飞行路径。输入参数为 waypoints（航点列表）。注意：此工具会返回详细的规划路径，请在后续生成 KMZ 时使用此路径或直接调用 generate_kmz。"
            ),
            StructuredTool.from_function(
                func=self.planning_agent.generate_kmz,
                name="generate_kmz",
                description="生成大疆司空2可导入的 KMZ(WPML) 文件。输入参数 waypoints 可选：如果之前已调用 generate_flight_plan，可不传 waypoints，系统将自动使用规划好的详细航线（推荐）。"
            )
        ]

        # 初始化标准 ReAct Agent
        dji_url = self.config.get("dji", {}).get("url", "")
        system_prompt = (
            "你是无人机综合指挥调度系统的 Orchestrator，负责通过调用工具解决用户需求。"
            f"大疆司空2网页控制台URL是: {dji_url}。"
            "你应该优先通过 get_coordinates 获取地点，然后进行航迹规划（generate_flight_plan），最后生成 KMZ（generate_kmz）。"
            "重要：generate_flight_plan 会生成包含数百个航点的详细路径。调用 generate_kmz 时，你可以不传 waypoints 参数，它会自动使用最近一次规划的结果。"
            "生成 KMZ 时，文件名固定为 mission.kmz（会自动覆盖旧文件）。"
            "在回答用户时，请保持专业且友好的语气，并简要说明你执行了哪些步骤。"
        )
        self.agent_executor = create_react_agent(self.llm, self.tools, prompt=system_prompt)
        
        logger.info("Orchestrator Agent (LangGraph create_react_agent) 初始化完成")

    def generate_flight_plan_wrapper(self, waypoints):
        """包装 PlanningAgent 的规划功能，对 LLM 隐藏过于庞大的坐标数据，防止上下文溢出"""
        result = self.planning_agent.generate_flight_plan(waypoints)
        if isinstance(result, dict) and "data" in result:
            data = result["data"]
            if "flight_path" in data and "waypoints" in data["flight_path"]:
                points = data["flight_path"]["waypoints"]
                if len(points) > 20:
                    # 关键修复：缩减返回给 LLM 的数据量，但保留摘要
                    summary_result = {
                        "status": "success",
                        "message": f"成功规划航线，共生成 {len(points)} 个详细航点。",
                        "data": {
                            "flight_path": {
                                "total_distance": data["flight_path"].get("total_distance"),
                                "estimated_flight_time": data["flight_path"].get("estimated_flight_time"),
                                "waypoint_count": len(points),
                                "waypoints": points[:5] + ["... (已省略其余航点以节省上下文) ..."] 
                            }
                        },
                        "note": "详细航点已保存在 PlanningAgent 状态中，直接调用 generate_kmz() 即可使用完整路径。"
                    }
                    return summary_result
        return result

    def reset_memory(self):
        self._history = []

    def _append_turn(self, user_text: str, assistant_text: str):
        self._history.append(("user", user_text))
        self._history.append(("assistant", assistant_text))
        max_len = self._history_max_pairs * 2
        if len(self._history) > max_len:
            self._history = self._history[-max_len:]

    def _format_trace_line(self, tool_name: str, args: dict, result) -> str:
        """为流式输出格式化中间步骤"""
        # 安全处理 result，确保它是字典
        res_dict = result if isinstance(result, dict) else {}
        
        if tool_name == "get_coordinates":
            poi = res_dict.get("poi") or {}
            aoi = res_dict.get("aoi_waypoints") or []
            return f"已获取 POI 坐标：纬度 {poi.get('latitude')}，经度 {poi.get('longitude')}，生成航点数：{len(aoi)}。\n\n"
        
        if tool_name == "generate_flight_plan":
            data = res_dict.get("data") or {}
            fp = data.get("flight_path") or {}
            return f"航迹规划完成：总航程 {fp.get('total_distance')}m，预计时长 {fp.get('estimated_flight_time')}s。\n\n"
        
        if tool_name == "generate_kmz":
            data = res_dict.get("data") or {}
            path = data.get("output_path") or res_dict.get("output_path") or ""
            return f"KMZ 生成完成，输出路径：{path}\n\n"
            
        return f"已执行 {tool_name}。\n\n"

    def process_instruction_stream(self, instruction: str):
        logger.info(f"Orchestrator 接收到指令: {instruction}")
        yield f"收到指令：{instruction}\n\n"

        optimized_instruction, _ = self.prompt_optimizer.optimize(instruction)
        query = optimized_instruction or instruction

        # 构造消息历史
        messages = []
        for role, content in self._history:
            if role == "user":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=query))

        full_response = ""
        kmz_path = ""

        try:
            # 使用 LangGraph 事件流 (updates 模式更适合追踪中间步骤)
            for chunk in self.agent_executor.stream({"messages": messages}, stream_mode="updates"):
                if "agent" in chunk:
                    last_msg = chunk["agent"]["messages"][-1]
                    # 指挥官决策（思考过程或工具调用）
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        for tc in last_msg.tool_calls:
                            yield f"指挥官决定执行：{tc['name']} ...\n"
                    elif last_msg.content:
                        # 最终回答或中间思考
                        content = last_msg.content
                        if content and content != full_response:
                            diff = content[len(full_response):]
                            full_response = content
                            yield diff
                
                elif "tools" in chunk:
                    # 工具执行结果
                    for msg in chunk["tools"]["messages"]:
                        try:
                            # 尝试解析结果并格式化
                            content_data = msg.content
                            if isinstance(content_data, str):
                                try:
                                    content_data = json.loads(content_data)
                                except:
                                    pass
                            
                            trace = self._format_trace_line(msg.name, {}, content_data)
                            yield trace
                        except Exception as te:
                            logger.error(f"格式化工具追踪失败: {te}")
                            yield f"工具 {msg.name} 执行完成。\n\n"

            # 保存对话历史
            if full_response:
                self._append_turn(instruction, full_response)

        except Exception as e:
            logger.error(f"LangGraph Agent 执行出错: {e}")
            yield f"\n\n[错误] Agent 执行遇到问题，正在尝试离线降级方案...\n\n"
            # 调用内部定义的离线降级逻辑
            yield self._fallback_execute(instruction)

    def _fallback_execute(self, instruction: str) -> str:
        """
        离线降级逻辑：在模型不可用或执行出错时，按预设的确定性流程执行。
        """
        target_name = self._extract_target_name(instruction)
        trace = []
        
        try:
            # 简化版降级
            coords = self.perception_agent.get_coordinates(target_name)
            trace.append(f"- PerceptionAgent.get_coordinates -> 完成")
            
            waypoints = (coords or {}).get("aoi_waypoints", [])
            # 调用 wrapper 以便记录航点并获得摘要
            plan_result = self.generate_flight_plan_wrapper(waypoints)
            trace.append(f"- PlanningAgent.generate_flight_plan -> 完成")
            
            # 自动使用 PlanningAgent 中记录的详细航点
            kmz = self.planning_agent.generate_kmz(output_filename="mission.kmz")
            trace.append(f"- PlanningAgent.generate_kmz -> 完成")
            
            kmz_data = kmz.get("data") or {} if isinstance(kmz, dict) else {}
            path = kmz_data.get("output_path", "")
            return f"离线模式执行成功：\n" + "\n".join(trace) + f"\n\nKMZ 路径: {path}"
        except Exception as fe:
            return f"离线降级也失败了: {fe}"

    def _extract_target_name(self, instruction: str) -> str:
        patterns = [r"对(.+?)进行", r"对(.+?)做", r"去(.+?)", r"到(.+?)执行"]
        for p in patterns:
            m = re.search(p, instruction)
            if m: return m.group(1).strip(" ，。,.")
        return instruction.strip()

    def process_instruction(self, instruction: str):
        return "".join(list(self.process_instruction_stream(instruction)))

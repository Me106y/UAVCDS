import os
import json
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
from utils.logger import logger
from tools.uav_tools import (
    fetch_dashboard_status,
    get_coordinates,
    generate_flight_plan,
    generate_kmz_file,
    check_airspace_conflict
)

class OrchestratorAgent:
    """
    总指挥官 (Orchestrator Agent)
    使用 LangGraph 的 ReAct 框架与 Qwen 模型，自动选择工具解决调度需求。
    """
    def __init__(self, config):
        self.config = config
        
        # 配置通义千问模型
        os.environ["DASHSCOPE_API_KEY"] = self.config["api_keys"]["dashscope"]
        self.llm = ChatOpenAI(
            api_key=os.environ["DASHSCOPE_API_KEY"],
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model=self.config["models"]["chat"],
            temperature=0.2,
            model_kwargs={"parallel_tool_calls": False}
        )
        
        # 准备工具箱
        self.tools = [
            fetch_dashboard_status,
            get_coordinates,
            generate_flight_plan,
            generate_kmz_file,
            check_airspace_conflict
        ]
        
        # 使用 LangGraph 的 create_react_agent 创建 Agent
        self.agent = create_react_agent(
            model=self.llm, 
            tools=self.tools
        )
        logger.info("Orchestrator Agent (LangGraph ReAct) 初始化完成")
        
    def process_instruction(self, instruction: str):
        logger.info(f"Orchestrator 接收到指令: {instruction}")
        try:
            # 额外补充系统提示，告知模型配置文件中的大疆司空2 URL
            dji_url = self.config.get("dji", {}).get("url", "")
            system_prompt = (
                f"你是一个无人机综合指挥调度系统的总指挥官。大疆司空2的网页控制台URL是: {dji_url}。"
                "如果需要查询大疆状态或信息，请使用对应工具访问该 URL。"
                "当用户要求按地点生成航线或 KMZ 时，必须严格按以下顺序执行："
                "1) 先调用 get_coordinates 获取 aoi_waypoints；"
                "2) 再把该 aoi_waypoints 原样传给 generate_flight_plan；"
                "3) 最后把同一份 aoi_waypoints 传给 generate_kmz_file。"
                "在 get_coordinates 返回之前，禁止调用 generate_flight_plan 或 generate_kmz_file。"
            )
            
            # 执行 ReAct 循环
            inputs = {"messages": [
                ("system", system_prompt),
                ("user", instruction)
            ]}
            
            # 使用 stream 方法以获取 Agent 每一步的执行过程
            final_message = ""
            kmz_output_path = ""
            for s in self.agent.stream(inputs, stream_mode="values"):
                # 获取最新的一条消息
                message = s["messages"][-1]
                
                # 记录模型的思考/工具调用
                if isinstance(message, AIMessage):
                    if message.tool_calls:
                        for tool_call in message.tool_calls:
                            logger.info(f"[模型思考] 决定调用工具: {tool_call['name']}, 参数: {tool_call['args']}")
                    elif message.content:
                        logger.info(f"[模型输出] {message.content}")
                        final_message = message.content
                        
                # 记录工具的执行结果
                elif isinstance(message, ToolMessage):
                    logger.info(f"[工具返回] {message.name} 的结果: {message.content}")
                    if message.name == "generate_kmz_file" and isinstance(message.content, str):
                        try:
                            payload = json.loads(message.content)
                            if isinstance(payload, dict):
                                kmz_output_path = (
                                    (payload.get("data") or {}).get("output_path") or kmz_output_path
                                )
                        except Exception:
                            pass

            if kmz_output_path and kmz_output_path not in final_message:
                final_message = f"{final_message}\n\nKMZ 绝对路径: {kmz_output_path}"
            return final_message
        except Exception as e:
            logger.error(f"Agent 执行出错: {e}")
            return f"执行过程中发生错误: {str(e)}"

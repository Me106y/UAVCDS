import streamlit as st
import json
import time
import asyncio
from utils.logger import logger
from agents.orchestrator import OrchestratorAgent
from utils.mcp_client import mcp_manager

# 加载配置
@st.cache_resource
def load_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# 初始化 Agent (为了避免每次重新渲染时重复初始化，使用 st.cache_resource)
@st.cache_resource
def get_orchestrator():
    config = load_config()
    return OrchestratorAgent(config)

config = load_config()

# 使用 get 安全获取配置，避免 KeyError
ui_title = config.get('ui_settings', {}).get('title', 'UAV 综合指挥调度系统')

st.set_page_config(
    page_title=ui_title,
    layout="wide"
)

st.title(ui_title)

# 初始化 session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示聊天历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 用户输入
if prompt := st.chat_input("请输入调度指令"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    logger.info(f"收到用户指令: {prompt}")

    with st.chat_message("assistant"):
        with st.spinner("调度指挥官正在思考中，并与各个 MCP 服务交互..."):
            agent = get_orchestrator()
            # 调用 Agent 的 ReAct 循环，这会真实触发 tools 中的 mcp_client
            final_response = agent.process_instruction(prompt)
            
            st.markdown(final_response)
        
    st.session_state.messages.append({"role": "assistant", "content": final_response})

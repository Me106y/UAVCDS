import json
import asyncio
from typing import Dict, Any, Optional
import threading
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from utils.logger import logger

class MCPManager:
    """
    管理与多个 MCP Server 的连接
    """
    def __init__(self, config_path: str = "mcp_settings.json"):
        self.config_path = config_path
        self.servers: Dict[str, StdioServerParameters] = {}
        self.sessions: Dict[str, ClientSession] = {}
        self.contexts: Dict[str, Any] = {} # 存储 stdio_client 上下文以防止被垃圾回收
        self._server_locks: Dict[str, threading.Lock] = {}
        self._lock_guard = threading.Lock()
        self._load_config()

    def _get_server_lock(self, server_name: str) -> threading.Lock:
        with self._lock_guard:
            if server_name not in self._server_locks:
                self._server_locks[server_name] = threading.Lock()
            return self._server_locks[server_name]

    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for server_name, server_config in config.get("mcpServers", {}).items():
                    # 确保 env 继承了系统的环境变量，特别是 PATH，否则 stdio 可能会找不到可执行文件
                    import os
                    env = os.environ.copy()
                    if server_config.get("env"):
                        env.update(server_config["env"])
                        
                    self.servers[server_name] = StdioServerParameters(
                        command=server_config["command"],
                        args=server_config.get("args", []),
                        env=env,
                        cwd=server_config.get("cwd")
                    )
            logger.info(f"MCPManager: 已加载 {len(self.servers)} 个 MCP 服务器配置。")
        except Exception as e:
            logger.error(f"MCPManager: 加载配置文件失败 - {e}")

    async def connect_server(self, server_name: str) -> bool:
        if server_name not in self.servers:
            logger.error(f"MCPManager: 找不到名为 {server_name} 的服务器配置。")
            return False

        if server_name in self.sessions:
            return True

        try:
            server_params = self.servers[server_name]
            logger.info(f"MCPManager: 正在尝试连接 {server_name} (command: {server_params.command} {' '.join(server_params.args)})")
            
            # 使用 asyncio.create_task 来保持上下文存活
            stdio_ctx = stdio_client(server_params)
            self.contexts[server_name] = stdio_ctx
            
            read, write = await stdio_ctx.__aenter__()
            session = ClientSession(read, write)
            await session.__aenter__()
            await session.initialize()
            
            self.sessions[server_name] = session
            logger.info(f"MCPManager: 成功连接到 {server_name}。")
            return True
        except Exception as e:
            logger.error(f"MCPManager: 连接 {server_name} 失败 - {e}")
            # 如果连接失败，打印一些有助于调试的信息
            logger.error(f"请检查服务 {server_name} 的 cwd 或命令是否正确。")
            return False

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        """
        调用指定 MCP Server 的工具
        """
        # 避免并发连接/并发调用同一 server 导致 stdio_client 上下文竞争
        server_lock = self._get_server_lock(server_name)
        await asyncio.to_thread(server_lock.acquire)

        try:
            if server_name not in self.sessions:
                connected = await self.connect_server(server_name)
                if not connected:
                    return {"error": f"无法连接到 MCP Server: {server_name}"}

            try:
                session = self.sessions[server_name]
                logger.info(f"MCPManager: 正在调用 {server_name} 的工具 [{tool_name}]，参数: {arguments}")
                result = await session.call_tool(tool_name, arguments)
                
                # 解析 MCP 协议返回的内容
                if hasattr(result, 'content') and len(result.content) > 0:
                    text_content = result.content[0].text
                    try:
                        parsed_result = json.loads(text_content)
                        logger.info(f"MCPManager: 工具 [{tool_name}] 返回 JSON 结果: {parsed_result}")
                        return parsed_result
                    except json.JSONDecodeError:
                        logger.info(f"MCPManager: 工具 [{tool_name}] 返回文本结果: {text_content}")
                        return text_content
                logger.info(f"MCPManager: 工具 [{tool_name}] 返回原始结果: {result}")
                return result
            except Exception as e:
                logger.error(f"MCPManager: 调用 {server_name}.{tool_name} 失败 - {e}")
                return {"error": str(e)}
        finally:
            server_lock.release()

    async def close_all(self):
        """关闭所有连接"""
        for name, session in self.sessions.items():
            try:
                await session.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"MCPManager: 关闭 {name} session 失败 - {e}")
                
        for name, ctx in self.contexts.items():
            try:
                await ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"MCPManager: 关闭 {name} stdio_client 失败 - {e}")
                
        self.sessions.clear()
        self.contexts.clear()
        logger.info("MCPManager: 已关闭所有 MCP 连接。")

# 全局单例
mcp_manager = MCPManager()

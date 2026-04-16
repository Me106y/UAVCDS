"""
MCP模块的模拟实现，用于测试和开发
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum


@dataclass
class Tool:
    """MCP工具定义"""
    name: str
    description: str
    inputSchema: Optional[Dict[str, Any]] = None


@dataclass 
class TextContent:
    """文本内容"""
    type: str = "text"
    text: str = ""


@dataclass
class CallToolResult:
    """工具调用结果"""
    content: List[TextContent]
    isError: bool = False


@dataclass
class ListToolsResult:
    """工具列表结果"""
    tools: List[Tool]


class Server:
    """模拟MCP服务器"""
    
    def __init__(self, name: str):
        self.name = name
        self._tools = {}
        self._tool_handlers = {}
    
    def list_tools(self):
        """装饰器：注册工具列表处理器"""
        def decorator(func):
            self._list_tools_handler = func
            return func
        return decorator
    
    def call_tool(self):
        """装饰器：注册工具调用处理器"""
        def decorator(func):
            self._call_tool_handler = func
            return func
        return decorator
    
    def get_capabilities(self, **kwargs):
        """获取服务器能力"""
        return {"tools": True}
    
    async def run(self, read_stream, write_stream, init_options):
        """运行服务器（模拟）"""
        import sys
        print(f"Mock MCP Server {self.name} running...", file=sys.stderr)


@dataclass
class InitializationOptions:
    """初始化选项"""
    server_name: str
    server_version: str
    capabilities: Dict[str, Any]


class stdio_server:
    """标准IO服务器上下文管理器"""
    
    async def __aenter__(self):
        return (None, None)  # 模拟读写流
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# 创建模块级别的导入
types = type('types', (), {
    'Tool': Tool,
    'TextContent': TextContent,
    'CallToolResult': CallToolResult,
    'ListToolsResult': ListToolsResult,
})

server = type('server', (), {
    'Server': Server,
})

server_models = type('server_models', (), {
    'InitializationOptions': InitializationOptions,
})

server_stdio = type('server_stdio', (), {
    'stdio_server': stdio_server,
})
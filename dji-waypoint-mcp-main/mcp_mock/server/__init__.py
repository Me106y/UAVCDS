"""
MCP服务器的模拟实现
"""

from typing import Any, Dict


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
        # MCP Server should not print to stdout
        import sys
        print(f"Mock MCP Server {self.name} running...", file=sys.stderr)
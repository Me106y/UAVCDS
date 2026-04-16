"""
MCP标准IO服务器的模拟实现
"""


class stdio_server:
    """标准IO服务器上下文管理器"""
    
    async def __aenter__(self):
        return (None, None)  # 模拟读写流
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
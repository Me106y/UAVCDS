"""
MCP服务器模型的模拟实现
"""

from typing import Any, Dict
from dataclasses import dataclass


@dataclass
class InitializationOptions:
    """初始化选项"""
    server_name: str
    server_version: str
    capabilities: Dict[str, Any]
"""
MCP类型定义的模拟实现
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass


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
class CallToolRequest:
    """工具调用请求"""
    name: str
    arguments: Optional[Dict[str, Any]] = None


@dataclass
class ListToolsRequest:
    """工具列表请求"""
    pass


@dataclass
class ListToolsResult:
    """工具列表结果"""
    tools: List[Tool]


@dataclass
class ImageContent:
    """图像内容"""
    type: str = "image"
    data: str = ""
    mimeType: str = "image/png"


@dataclass
class EmbeddedResource:
    """嵌入式资源"""
    type: str = "resource"
    resource: Dict[str, Any] = None
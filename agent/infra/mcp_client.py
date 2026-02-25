"""
MCP (Model Context Protocol) 客户端

使用 OpenHands 的 MCP Client 实现
支持连接外部 MCP Servers 并获取工具
"""
import asyncio
from typing import List, Optional, Dict, Any
import shutil

from openhands.mcp.client import MCPClient
from openhands.mcp.utils import (
    create_mcp_clients,
    convert_mcp_clients_to_tools,
    fetch_mcp_tools_from_config,
)
from openhands.sdk.tool import Tool

from .mcp_config import (
    MCPConfig,
    MCPSSEServerConfig,
    MCPSHTTPServerConfig,
    MCPStdioServerConfig,
)


class MCPClientManager:
    """
    MCP 客户端管理器
    
    负责：
    - 创建和管理 MCP 客户端连接
    - 将 MCP 工具转换为 SDK Tool 格式
    - 调用 MCP 工具
    """
    
    def __init__(self, config: Optional[MCPConfig] = None):
        self.config = config or MCPConfig()
        self._clients: List[MCPClient] = []
        self._tools: List[Tool] = []
        self._initialized = False
    
    async def initialize(self) -> List[Tool]:
        """
        初始化 MCP 客户端并获取工具
        
        Returns:
            MCP 工具列表
        """
        if self._initialized:
            return self._tools
        
        # 创建 MCP 客户端
        self._clients = await create_mcp_clients(
            sse_servers=self.config.sse_servers,
            shttp_servers=self.config.shttp_servers,
            stdio_servers=self.config.stdio_servers if self._should_use_stdio() else [],
        )
        
        # 转换为 SDK Tool 格式
        self._tools = convert_mcp_clients_to_tools(self._clients)
        
        self._initialized = True
        return self._tools
    
    def _should_use_stdio(self) -> bool:
        """判断是否使用 Stdio 服务器"""
        import sys
        # Windows 上禁用 MCP
        if sys.platform == "win32":
            return False
        # 有 stdio 服务器配置时使用
        return len(self.config.stdio_servers) > 0
    
    def get_tools(self) -> List[Tool]:
        """获取 MCP 工具"""
        return self._tools
    
    def get_clients(self) -> List[MCPClient]:
        """获取 MCP 客户端"""
        return self._clients
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        if not self._initialized:
            await self.initialize()
        
        # 查找匹配的客户端
        for client in self._clients:
            if tool_name in [tool.name for tool in client.tools]:
                return await client.call_tool(tool_name, arguments)
        
        raise ValueError(f"MCP tool not found: {tool_name}")
    
    async def close(self) -> None:
        """关闭所有客户端连接"""
        for client in self._clients:
            if client.client:
                async with client.client:
                    pass  # 关闭连接
        self._clients = []
        self._initialized = False


# ========== 全局 MCP 客户端管理器 ==========

_default_mcp_manager: Optional[MCPClientManager] = None


def get_mcp_client_manager(config: Optional[MCPConfig] = None) -> MCPClientManager:
    """获取全局 MCP 客户端管理器"""
    global _default_mcp_manager
    if _default_mcp_manager is None:
        _default_mcp_manager = MCPClientManager(config)
    return _default_mcp_manager


async def initialize_mcp_tools(config: Optional[MCPConfig] = None) -> List[Tool]:
    """
    初始化 MCP 工具
    
    便捷函数，用于快速获取 MCP 工具
    """
    manager = get_mcp_client_manager(config)
    return await manager.initialize()


def get_mcp_tools() -> List[Tool]:
    """
    获取 MCP 工具（同步版本）
    
    注意：如果未初始化，返回空列表
    """
    global _default_mcp_manager
    if _default_mcp_manager is None:
        return []
    return _default_mcp_manager.get_tools()

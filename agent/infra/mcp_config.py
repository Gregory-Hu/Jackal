"""
MCP (Model Context Protocol) 配置

使用 OpenHands 的 MCP 配置系统
支持三种连接方式：SSE、SHTTP、Stdio
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class MCPSSEServerConfig:
    """SSE MCP 服务器配置"""
    url: str
    api_key: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "api_key": self.api_key,
        }


@dataclass
class MCPSHTTPServerConfig:
    """SHTTP MCP 服务器配置"""
    url: str
    api_key: Optional[str] = None
    timeout: Optional[float] = 60.0  # 工具调用超时（秒）
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "api_key": self.api_key,
            "timeout": self.timeout,
        }


@dataclass
class MCPStdioServerConfig:
    """Stdio MCP 服务器配置"""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "env": self.env,
        }


@dataclass
class MCPConfig:
    """
    MCP 配置
    
    用于配置 MCP 客户端连接的服务器列表
    """
    sse_servers: List[MCPSSEServerConfig] = field(default_factory=list)
    shttp_servers: List[MCPSHTTPServerConfig] = field(default_factory=list)
    stdio_servers: List[MCPStdioServerConfig] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPConfig":
        """从字典创建配置"""
        sse_servers = [
            MCPSSEServerConfig(**server)
            for server in data.get("sse_servers", [])
        ]
        shttp_servers = [
            MCPSHTTPServerConfig(**server)
            for server in data.get("shttp_servers", [])
        ]
        stdio_servers = [
            MCPStdioServerConfig(**server)
            for server in data.get("stdio_servers", [])
        ]
        
        return cls(
            sse_servers=sse_servers,
            shttp_servers=shttp_servers,
            stdio_servers=stdio_servers,
        )
    
    @classmethod
    def from_toml(cls, toml_path: str) -> "MCPConfig":
        """从 TOML 文件加载配置"""
        import tomllib
        
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        
        mcp_data = data.get("mcp", {})
        return cls.from_dict(mcp_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "sse_servers": [s.to_dict() for s in self.sse_servers],
            "shttp_servers": [s.to_dict() for s in self.shttp_servers],
            "stdio_servers": [s.to_dict() for s in self.stdio_servers],
        }


# ========== 默认配置 ==========

def get_default_mcp_config() -> MCPConfig:
    """
    获取默认 MCP 配置
    
    示例配置，实际使用时请修改
    """
    return MCPConfig(
        # SSE 服务器示例
        sse_servers=[
            # MCPSSEServerConfig(
            #     url="https://your-mcp-server.com/sse",
            #     api_key="your-api-key"
            # )
        ],
        
        # SHTTP 服务器示例
        shttp_servers=[
            # MCPSHTTPServerConfig(
            #     url="http://localhost:8000/mcp",
            #     timeout=60.0
            # )
        ],
        
        # Stdio 服务器示例（本地运行）
        stdio_servers=[
            # MCPStdioServerConfig(
            #     name="tavily-search",
            #     command="npx",
            #     args=["-y", "tavily-mcp@0.2.1"],
            #     env={"TAVILY_API_KEY": "your-api-key"}
            # ),
            # MCPStdioServerConfig(
            #     name="filesystem",
            #     command="npx",
            #     args=["-y", "@modelcontextprotocol/server-filesystem", "./workspace"],
            #     env={}
            # )
        ],
    )

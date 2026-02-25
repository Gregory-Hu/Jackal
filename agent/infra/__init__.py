"""
基础设施层
"""
from .messaging import (
    MessageType,
    MessagePriority,
    Message,
    MessageBus,
    get_message_bus,
    set_message_bus,
)

from .registry import (
    ModuleType,
    ModuleStatus,
    ModuleInfo,
    ModuleRegistry,
    get_module_registry,
)

from .mcp_config import (
    MCPConfig,
    MCPSSEServerConfig,
    MCPSHTTPServerConfig,
    MCPStdioServerConfig,
)

from .mcp_client import (
    MCPClientManager,
    get_mcp_client_manager,
    initialize_mcp_tools,
    get_mcp_tools,
)

from .fault import (
    # Enums
    FaultSeverity,
    FaultStatus,
    FaultType,
    # Data classes
    Fault,
    FaultReport,
    EscalationNotification,
    HumanReview,
    # Classes
    FaultDetector,
    FaultReporter,
    EscalationManager,
    # Functions
    detect_faults,
    escalate_fault,
)

__all__ = [
    # Messaging (Internal Message Bus)
    "MessageType",
    "MessagePriority",
    "Message",
    "MessageBus",
    "get_message_bus",
    "set_message_bus",

    # Registry
    "ModuleType",
    "ModuleStatus",
    "ModuleInfo",
    "ModuleRegistry",
    "get_module_registry",

    # MCP (Model Context Protocol)
    "MCPConfig",
    "MCPSSEServerConfig",
    "MCPSHTTPServerConfig",
    "MCPStdioServerConfig",
    "MCPClientManager",
    "get_mcp_client_manager",
    "initialize_mcp_tools",
    "get_mcp_tools",

    # Fault Detection & Escalation
    "FaultSeverity",
    "FaultStatus",
    "FaultType",
    "Fault",
    "FaultReport",
    "EscalationNotification",
    "HumanReview",
    "FaultDetector",
    "FaultReporter",
    "EscalationManager",
    "detect_faults",
    "escalate_fault",
]

"""
服务层：执行智能体

使用 OpenHands SDK 的 Tools 系统替代原有的 ExecutionAgent 架构

OpenHands 内置工具：
- BashTool: 执行 bash 命令
- FileEditorTool: 文件编辑
- TaskTrackerTool: 任务跟踪
- TerminalTool: 终端执行

自定义工具请继承 openhands.sdk.tool 中的 ToolDefinition
"""

# 从 OpenHands SDK 导入内置工具
from openhands.tools import (
    BashTool,
    FileEditorTool,
    TaskTrackerTool,
)

# 导出工具创建函数
__all__ = [
    "BashTool",
    "FileEditorTool", 
    "TaskTrackerTool",
]

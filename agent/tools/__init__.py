"""
Tools 包

使用 OpenHands SDK 的 Tool 系统

自定义工具示例：
```python
from openhands.sdk.tool import ToolDefinition, Action, Observation
from pydantic import Field

class MyAction(Action):
    param: str = Field(description="参数描述")

class MyObservation(Observation):
    result: str

class MyTool(ToolDefinition):
    @classmethod
    def create(cls, conv_state):
        return [cls(
            description="工具描述",
            action_type=MyAction,
            observation_type=MyObservation,
        )]
```
"""

# 从 OpenHands SDK 导入工具相关类
from openhands.sdk.tool import (
    Tool,
    ToolDefinition,
    Action,
    Observation,
    register_tool,
)

__all__ = [
    "Tool",
    "ToolDefinition",
    "Action",
    "Observation",
    "register_tool",
]

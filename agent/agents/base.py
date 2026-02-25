"""
基础 Agent 类定义

使用 OpenHands SDK 的 Agent 作为底层执行引擎
保留 JD (Job Description) 和 Skills/SOPs 作为上层编排逻辑
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from openhands.sdk import LLM, Agent, Conversation
from openhands.sdk.tool import Tool


@dataclass
class AgentConfig:
    """
    Agent 配置
    
    整合 OpenHands SDK Agent 配置和你的 JD/SOP 概念
    """
    # OpenHands SDK 配置
    llm: LLM
    tools: List[Tool]
    
    # 你的独特配置
    jd_id: str = ""           # Job Description ID
    role: str = ""            # Role 名称
    system_prompt: Optional[str] = None
    
    # 可选配置
    max_iterations: int = 100
    enable_memory: bool = True
    
    def to_openhands_agent(self) -> Agent:
        """转换为 OpenHands SDK Agent"""
        return Agent(
            llm=self.llm,
            tools=self.tools,
            max_iterations=self.max_iterations,
        )


class BaseAgent(ABC):
    """
    自定义 Agent 基类
    
    在 OpenHands SDK Agent 之上封装你的业务逻辑
    """

    def __init__(
        self,
        config: AgentConfig,
        name: str = "custom-agent",
    ):
        self.config = config
        self.name = name
        self.llm = config.llm
        
        # 创建底层 SDK Agent
        self._agent = config.to_openhands_agent()
        
        # 系统提示词
        self.system_prompt = config.system_prompt or self._default_system_prompt()

    @abstractmethod
    def _default_system_prompt(self) -> str:
        """返回默认的系统提示词"""
        pass

    @abstractmethod
    def get_tools(self) -> List[str]:
        """返回 Agent 可用的工具列表名称"""
        pass

    def create_conversation(self, workspace: str) -> Conversation:
        """创建对话实例"""
        return Conversation(
            agent=self._agent,
            workspace=workspace,
        )

    async def run(self, task: str, workspace: str) -> str:
        """
        运行 Agent 执行任务
        
        Args:
            task: 任务描述
            workspace: 工作目录
            
        Returns:
            执行结果
        """
        conversation = self.create_conversation(workspace)
        conversation.send_message(task)
        conversation.run()

        # 返回最后的事件内容
        result = conversation.state.events[-1]
        if hasattr(result, "llm_message"):
            from openhands.sdk.llm import content_to_str
            return "".join(content_to_str(result.llm_message.content))
        return str(result)

    def get_agent(self) -> Agent:
        """获取底层的 OpenHands SDK Agent"""
        return self._agent


# ========== 预定义的 Agent 工厂 ==========

def create_default_agent(
    llm: LLM,
    jd_id: str = "",
    role: str = "junior",
) -> BaseAgent:
    """
    创建默认 Agent
    
    使用 OpenHands 的默认工具集
    """
    from openhands.tools.preset.default import get_default_agent as get_default_tools
    
    # 获取默认工具
    default_agent = get_default_tools(llm=llm, cli_mode=True)
    
    # 创建配置
    config = AgentConfig(
        llm=llm,
        tools=default_agent.tools,
        jd_id=jd_id,
        role=role,
    )
    
    # 创建自定义 Agent
    class DefaultAgent(BaseAgent):
        def _default_system_prompt(self) -> str:
            return f"你是一个 {role} 工程师，负责完成软件开发任务。"
        
        def get_tools(self) -> List[str]:
            return ["bash", "file_editor", "task_tracker"]
    
    return DefaultAgent(config=config, name=f"agent-{jd_id}")

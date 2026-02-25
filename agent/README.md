# OpenHands Agent 框架 - 四层架构

基于 **OpenHands SDK** + **显式任务状态机 + 任务清单驱动** 的可控 Agent 框架，
采用清晰的四层架构设计，支持标准 MCP (Model Context Protocol) 协议。

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────┐
│              Application Layer (应用层)                  │
│  ┌─────────────┬─────────────┬─────────────────────────┐ │
│  │Orchestration│   Meeting   │       Reporting         │ │
│  └─────────────┴─────────────┴─────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              Service Layer (服务层)                      │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  OpenHands SDK Tools (Bash, FileEditor, Terminal)   │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│               Memory Layer (记忆层)                      │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Cognitive Memory + Notebook Memory + OpenHands     │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│        Infrastructure Layer (基础设施层)                 │
│  ┌─────────────┬─────────────┬─────────────────────────┐ │
│  │ MessageBus  │ MCP Client  │  Module Registry        │ │
│  │ (Internal)  │ (Standard)  │                         │ │
│  └─────────────┴─────────────┴─────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

**第一步：复制配置文件**

```bash
copy .env.example .env
```

**第二步：编辑 `.env` 文件，填入你的 API Key**

```bash
# LLM 配置（支持任何 LiteLLM 兼容的提供商）
LLM_API_KEY=sk-your-api-key-here
LLM_MODEL=anthropic/claude-sonnet-4-5-20250929
LLM_BASE_URL=https://api.anthropic.com
```

**第三步：验证配置**

```bash
python test_migration.py
```

### 3. 运行演示

```bash
# 迁移演示
python examples\migration_demo.py

# 简单 Agent 示例
python examples\simple_agent.py

# 工作流示例
python examples\workflow.py
```

## 📦 核心组件

### 基础设施层 (Infrastructure)

| 模块 | 职责 | OpenHands SDK |
|------|------|------|
| **MessageBus** | 内部消息总线（发布/订阅） | ❌ 自研 |
| **MCP Client** | 标准 MCP 客户端 | ✅ 使用 SDK |
| **Module Registry** | 模块注册、发现、健康检查 | ❌ 自研 |

### 记忆层 (Memory)

| 模块 | 职责 | OpenHands SDK |
|------|------|------|
| **Cognitive Memory** | 长期认知结果存储 | ✅ 集成 SDK Memory |
| **Notebook Memory** | 短期任务状态记录 | ✅ 集成 SDK Memory |

### 服务层 (Service)

| 模块 | 职责 | OpenHands SDK |
|------|------|------|
| **Tools** | 执行工具 | ✅ 使用 SDK Tools |
| **BashTool** | 执行 bash 命令 | ✅ SDK 内置 |
| **FileEditorTool** | 文件编辑 | ✅ SDK 内置 |
| **TaskTrackerTool** | 任务跟踪 | ✅ SDK 内置 |

### 应用层 (Application)

| 服务 | 职责 | OpenHands SDK |
|------|------|------|
| **Orchestration** | 任务分解、智能体调度 | ✅ 基于 SDK Agent |
| **Meeting** | 多 Agent 协作 | ❌ 自研 |
| **Reporting** | 事件监听、报告生成 | ❌ 自研 |

## 🔌 MCP (Model Context Protocol) 集成

### 配置 MCP 服务器

在 `config.toml` 或代码中配置：

```python
from infra import MCPConfig, MCPSSEServerConfig, MCPStdioServerConfig

mcp_config = MCPConfig(
    # SSE 服务器
    sse_servers=[
        MCPSSEServerConfig(
            url="https://your-mcp-server.com/sse",
            api_key="your-api-key"
        )
    ],
    
    # Stdio 服务器（本地运行）
    stdio_servers=[
        MCPStdioServerConfig(
            name="tavily-search",
            command="npx",
            args=["-y", "tavily-mcp@0.2.1"],
            env={"TAVILY_API_KEY": "your-api-key"}
        )
    ],
)
```

### 使用 MCP 工具

```python
from infra import initialize_mcp_tools

# 初始化 MCP 工具
mcp_tools = await initialize_mcp_tools(mcp_config)

# MCP 工具会自动添加到 Agent 中
```

## 💡 使用示例

### 使用 OpenHands SDK Agent

```python
from openhands.sdk import LLM, Conversation
from openhands.tools.preset.default import get_default_agent

# 创建 LLM
llm = LLM(
    model="anthropic/claude-sonnet-4-5-20250929",
    api_key="your-api-key",
)

# 创建默认 Agent
agent = get_default_agent(llm=llm, cli_mode=True)

# 创建对话
conversation = Conversation(
    agent=agent,
    workspace="./workspace",
)

# 执行任务
conversation.send_message("在 workspace 目录下创建一个 README.md 文件")
conversation.run()
```

### 使用 Orchestration 服务

```python
from application import OrchestrationService
from openhands.sdk import LLM

# 初始化
llm = LLM(model="anthropic/claude-sonnet-4-5-20250929", api_key="...")
orchestrator = OrchestrationService(llm=llm)

# 创建 Agent
agent_info = await orchestrator.create_agent(
    agent_type="default",
    workspace="./workspace",
)

# 提交任务
task_id = await orchestrator.submit_task({
    "name": "分析代码结构",
    "description": "分析 workspace 目录下的代码结构",
})

# 查询状态
status = orchestrator.get_task_status(task_id)
```

### 使用自定义 Agent

```python
from agents import BaseAgent, AgentConfig
from openhands.sdk import LLM
from openhands.tools import BashTool, FileEditorTool

# 创建 LLM
llm = LLM(model="anthropic/claude-sonnet-4-5-20250929", api_key="...")

# 创建配置
config = AgentConfig(
    llm=llm,
    tools=[BashTool.create(), FileEditorTool.create()],
    jd_id="junior_developer",
    role="junior",
)

# 创建自定义 Agent
class MyAgent(BaseAgent):
    def _default_system_prompt(self) -> str:
        return "你是一个初级软件工程师，负责完成开发任务。"
    
    def get_tools(self) -> list[str]:
        return ["bash", "file_editor"]

agent = MyAgent(config=config, name="my-agent")

# 执行任务
result = await agent.run(
    task="创建一个 Python 脚本，打印 Hello World",
    workspace="./workspace",
)
```

## 📁 项目结构

```
agent/
├── infra/                     # 基础设施层
│   ├── messaging.py           # 内部消息总线
│   ├── mcp_config.py          # MCP 配置
│   ├── mcp_client.py          # MCP 客户端
│   └── registry.py            # 模块注册表
├── memory/                    # 记忆层
│   └── memory_service.py      # 记忆服务（集成 OpenHands Memory）
├── agents/                    # Agent 定义
│   ├── base.py                # Agent 基类（基于 OpenHands SDK）
│   ├── coder.py               # 编码 Agent
│   └── reviewer.py            # 审查 Agent
├── application/               # 应用层
│   ├── orchestration.py       # 编排服务（基于 OpenHands SDK）
│   ├── meeting.py             # 会议服务
│   └── reporting.py           # 报告服务
├── services/                  # 服务层
│   └── __init__.py            # 导出 OpenHands Tools
├── tools/                     # 自定义工具
│   └── __init__.py            # 导出 OpenHands Tool 系统
├── jd/                        # Job Descriptions
├── skills/                    # 技能定义 (Markdown)
├── sops/                      # 标准操作程序 (Markdown)
├── duty_skills/               # 职责技能 (Markdown)
├── orchestration_skills/      # 编排技能 (Markdown)
├── examples/                  # 示例代码
│   ├── migration_demo.py      # 迁移演示
│   ├── simple_agent.py        # 简单 Agent
│   └── workflow.py            # 工作流示例
├── workspace/                 # 工作目录
├── .env                       # 环境变量配置
├── config.py                  # 配置加载
├── requirements.txt           # 依赖
└── test_migration.py          # 迁移验证测试
```

## 🔄 迁移说明

本项目已从自定义实现迁移到 OpenHands SDK：

### 已替换的组件

| 原组件 | 新组件 | 说明 |
|--------|--------|------|
| 自定义 MCP | OpenHands MCP Client | 现在支持标准 MCP 协议 |
| 自定义 Agent | OpenHands SDK Agent | 使用 SDK 的事件驱动循环 |
| 自定义 Tools | OpenHands Tools | 使用 SDK 的 Action-Observation 模式 |
| 自定义 Event | OpenHands Events | 使用 SDK 的 EventStream |

### 保留的独特功能

- JD (Job Description) 系统
- Skills/SOPs Markdown 文档
- Meeting 多 Agent 协作
- Reporting 报告生成
- 四层架构设计

## 📚 参考资源

- [OpenHands SDK 文档](https://docs.openhands.dev/sdk)
- [OpenHands GitHub](https://github.com/OpenHands/OpenHands)
- [MCP 协议规范](https://modelcontextprotocol.io)
- [OpenHands Software Agent SDK 论文](https://arxiv.org/abs/2511.03690)

## 🧪 测试

```bash
# 运行迁移验证测试
python test_migration.py

# 运行简单 Agent 测试
python examples\simple_agent.py
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

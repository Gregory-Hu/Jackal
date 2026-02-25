"""
迁移示例：使用 OpenHands SDK 的完整演示

此示例展示如何使用迁移后的架构：
1. 使用 OpenHands SDK 的 LLM 和 Agent
2. 使用 MCP Client 连接外部 MCP 服务器
3. 使用 Memory 服务
4. 使用 Orchestration 服务编排任务
"""
import asyncio
import os

# 导入 OpenHands SDK
from openhands.sdk import LLM, Conversation
from openhands.tools.preset.default import get_default_agent

# 导入你的模块
from infra import (
    MCPConfig, MCPSSEServerConfig, MCPStdioServerConfig,
    get_mcp_client_manager, initialize_mcp_tools,
)
from memory import get_memory_service
from application import OrchestrationService


async def main():
    """主函数"""
    print("=" * 60)
    print("OpenHands SDK 迁移示例")
    print("=" * 60)
    
    # ========== 1. 初始化 LLM ==========
    print("\n[1] 初始化 LLM...")
    
    # 从环境变量读取配置
    llm_model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_base_url = os.getenv("LLM_BASE_URL", "")
    
    if not llm_api_key:
        print("⚠️ 警告：LLM_API_KEY 未设置，部分功能可能不可用")
        print("   请在 .env 文件中配置 LLM_API_KEY")
    
    llm = LLM(
        model=llm_model,
        api_key=llm_api_key,
        base_url=llm_base_url,
    )
    print(f"✓ LLM 已初始化：{llm_model}")
    
    # ========== 2. 初始化 MCP 工具（可选） ==========
    print("\n[2] 初始化 MCP 工具...")
    
    # 配置 MCP 服务器
    mcp_config = MCPConfig(
        # SSE 服务器示例
        sse_servers=[
            # MCPSSEServerConfig(
            #     url="https://your-mcp-server.com/sse",
            #     api_key="your-api-key"
            # )
        ],
        
        # Stdio 服务器示例（本地运行）
        stdio_servers=[
            # MCPStdioServerConfig(
            #     name="tavily-search",
            #     command="npx",
            #     args=["-y", "tavily-mcp@0.2.1"],
            #     env={"TAVILY_API_KEY": "your-api-key"}
            # )
        ],
    )
    
    # 初始化 MCP 工具
    mcp_tools = await initialize_mcp_tools(mcp_config)
    print(f"✓ 加载了 {len(mcp_tools)} 个 MCP 工具")
    
    # ========== 3. 初始化记忆服务 ==========
    print("\n[3] 初始化记忆服务...")
    
    memory = get_memory_service(storage_path="./workspace/memory")
    print(f"✓ 记忆服务已初始化")
    
    # ========== 4. 使用 OpenHands Agent 执行简单任务 ==========
    print("\n[4] 使用 OpenHands Agent 执行任务...")
    
    # 创建默认 Agent
    agent = get_default_agent(llm=llm, cli_mode=True)
    
    # 创建工作区
    workspace = "./workspace"
    os.makedirs(workspace, exist_ok=True)
    
    # 创建对话
    conversation = Conversation(
        agent=agent,
        workspace=workspace,
    )
    
    # 发送消息
    task = "在 workspace 目录下创建一个名为 hello.txt 的文件，内容为 'Hello from OpenHands SDK!'"
    print(f"任务：{task}")
    
    conversation.send_message(task)
    conversation.run()
    
    # 获取结果
    result = conversation.state.events[-1]
    if hasattr(result, "llm_message"):
        from openhands.sdk.llm import content_to_str
        result_content = "".join(content_to_str(result.llm_message.content))
        print(f"结果：{result_content[:200]}...")
    
    print("✓ 任务执行完成")
    
    # ========== 5. 使用 Orchestration 服务 ==========
    print("\n[5] 使用 Orchestration 服务编排任务...")
    
    orchestrator = OrchestrationService(
        orchestrator_id="demo_orchestrator",
        memory_service=memory,
        llm=llm,
    )
    
    # 创建 Agent
    agent_info = await orchestrator.create_agent(
        agent_type="default",
        workspace=workspace,
    )
    print(f"✓ Agent 已创建：{agent_info['agent_id']}")
    
    # 提交任务
    task_id = await orchestrator.submit_task({
        "name": "分析项目结构",
        "description": "列出 workspace 目录下的所有文件和文件夹",
        "agent_type": "default",
    })
    print(f"✓ 任务已提交：{task_id}")
    
    # 获取任务状态
    task_status = orchestrator.get_task_status(task_id)
    print(f"任务状态：{task_status['status']}")
    
    # ========== 6. 查看服务状态 ==========
    print("\n[6] 服务状态...")
    
    status = orchestrator.get_status()
    print(f"编排服务状态:")
    print(f"  - Agent 数量：{status['managed_agents']}")
    print(f"  - MCP 工具数量：{status['mcp_tools']}")
    print(f"  - LLM 已初始化：{status['llm_initialized']}")
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

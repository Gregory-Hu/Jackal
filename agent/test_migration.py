"""
迁移验证测试脚本

测试迁移后的各个组件是否正常工作
"""
import asyncio
import os
import sys


def test_imports():
    """测试所有模块是否可以正常导入"""
    print("\n[测试 1] 测试模块导入...")
    
    try:
        # 测试 OpenHands SDK 导入
        from openhands.sdk import LLM, Agent, Conversation
        print("  ✓ openhands.sdk 导入成功")
        
        # 测试 OpenHands Tools 导入
        from openhands.tools import BashTool, FileEditorTool
        print("  ✓ openhands.tools 导入成功")
        
        # 测试 OpenHands MCP 导入
        from openhands.mcp.client import MCPClient
        print("  ✓ openhands.mcp 导入成功")
        
        # 测试你的模块导入
        from infra import (
            Message, MessageType, MessageBus,
            MCPConfig, get_mcp_client_manager,
        )
        print("  ✓ infra 模块导入成功")
        
        from memory import MemoryService, get_memory_service
        print("  ✓ memory 模块导入成功")
        
        from agents import BaseAgent, AgentConfig
        print("  ✓ agents 模块导入成功")
        
        from application import OrchestrationService
        print("  ✓ application 模块导入成功")
        
        print("\n✅ 所有模块导入测试通过！")
        return True
        
    except ImportError as e:
        print(f"\n❌ 模块导入失败：{e}")
        return False


def test_llm_config():
    """测试 LLM 配置"""
    print("\n[测试 2] 测试 LLM 配置...")
    
    from config import get_config
    
    config = get_config()
    
    if config.is_llm_configured:
        print(f"  ✓ LLM 已配置：{config.llm_model}")
        print("\n✅ LLM 配置测试通过！")
        return True
    else:
        print("  ⚠️ LLM 未配置，请在 .env 文件中设置 LLM_API_KEY")
        print("\n⚠️ LLM 配置测试跳过")
        return None  # 返回 None 表示跳过


def test_message_bus():
    """测试内部消息总线"""
    print("\n[测试 3] 测试消息总线...")
    
    from infra import Message, MessageType, get_message_bus
    
    bus = get_message_bus()
    
    # 测试消息创建
    msg = Message(
        message_type=MessageType.START_TASK,
        source="test",
        payload={"task": "test_task"},
    )
    print(f"  ✓ 消息创建成功：{msg.message_id}")
    
    # 测试消息序列化
    msg_dict = msg.to_dict()
    msg_json = msg.to_json()
    print(f"  ✓ 消息序列化成功")
    
    # 测试消息反序列化
    msg2 = Message.from_dict(msg_dict)
    print(f"  ✓ 消息反序列化成功")
    
    print("\n✅ 消息总线测试通过！")
    return True


def test_memory_service():
    """测试记忆服务"""
    print("\n[测试 4] 测试记忆服务...")
    
    from memory import get_memory_service, MemoryType
    
    # 清理旧的测试数据
    import shutil
    test_path = "./workspace/test_memory"
    if os.path.exists(test_path):
        shutil.rmtree(test_path)
    
    memory = get_memory_service(storage_path=test_path)
    
    # 测试存储知识
    entry_id = memory.store_knowledge(
        key="test_key",
        value={"data": "test_value"},
        tags=["test", "migration"],
        created_by="test_script",
    )
    print(f"  ✓ 知识存储成功：{entry_id}")
    
    # 测试获取知识
    value = memory.get_knowledge("test_key")
    assert value == {"data": "test_value"}, f"Expected test_value, got {value}"
    print(f"  ✓ 知识获取成功")
    
    # 测试存储任务状态
    memory.store_task_state(
        task_id="test_task",
        state={"status": "running"},
    )
    print(f"  ✓ 任务状态存储成功")
    
    # 测试获取任务状态
    state = memory.get_task_state("test_task")
    assert state["status"] == "running", f"Expected running, got {state}"
    print(f"  ✓ 任务状态获取成功")
    
    print("\n✅ 记忆服务测试通过！")
    return True


def test_mcp_config():
    """测试 MCP 配置"""
    print("\n[测试 5] 测试 MCP 配置...")
    
    from infra import MCPConfig, MCPSSEServerConfig, MCPStdioServerConfig
    
    # 测试配置创建
    config = MCPConfig(
        sse_servers=[
            MCPSSEServerConfig(url="https://example.com/sse", api_key="test_key"),
        ],
        stdio_servers=[
            MCPStdioServerConfig(
                name="test_server",
                command="echo",
                args=["hello"],
                env={"TEST": "value"},
            ),
        ],
    )
    
    print(f"  ✓ MCP 配置创建成功")
    print(f"    - SSE 服务器：{len(config.sse_servers)}")
    print(f"    - Stdio 服务器：{len(config.stdio_servers)}")
    
    # 测试序列化
    config_dict = config.to_dict()
    print(f"  ✓ MCP 配置序列化成功")
    
    # 测试反序列化
    config2 = MCPConfig.from_dict(config_dict)
    print(f"  ✓ MCP 配置反序列化成功")
    
    print("\n✅ MCP 配置测试通过！")
    return True


async def test_orchestration_service():
    """测试编排服务"""
    print("\n[测试 6] 测试编排服务...")
    
    from application import OrchestrationService
    from memory import get_memory_service
    
    # 清理旧的测试数据
    import shutil
    test_path = "./workspace/test_orchestration"
    if os.path.exists(test_path):
        shutil.rmtree(test_path)
    
    memory = get_memory_service(storage_path=test_path)
    
    orchestrator = OrchestrationService(
        orchestrator_id="test_orchestrator",
        memory_service=memory,
    )
    
    # 测试服务状态
    status = orchestrator.get_status()
    print(f"  ✓ 编排服务状态查询成功")
    print(f"    - Agent 数量：{status['managed_agents']}")
    print(f"    - LLM 已初始化：{status['llm_initialized']}")
    
    # 测试 SOP 加载
    # 创建一个测试 SOP 文件
    os.makedirs("./sops", exist_ok=True)
    with open("./sops/test_sop.md", "w") as f:
        f.write("""---
sop_id: test_sop
name: 测试 SOP
description: 用于测试的 SOP
---

# 测试 SOP
""")
    
    sop = orchestrator.load_sop("./sops/test_sop.md")
    print(f"  ✓ SOP 加载成功：{sop.sop_id}")
    
    # 测试任务提交
    task_id = await orchestrator.submit_task({
        "name": "测试任务",
        "description": "这是一个测试任务",
    })
    print(f"  ✓ 任务提交成功：{task_id}")
    
    # 测试任务状态查询
    task_status = orchestrator.get_task_status(task_id)
    print(f"  ✓ 任务状态查询成功：{task_status['status']}")
    
    # 清理测试 SOP
    os.remove("./sops/test_sop.md")
    
    print("\n✅ 编排服务测试通过！")
    return True


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("OpenHands SDK 迁移验证测试")
    print("=" * 60)
    
    results = {
        "imports": test_imports(),
        "llm_config": test_llm_config(),
        "message_bus": test_message_bus(),
        "memory_service": test_memory_service(),
        "mcp_config": test_mcp_config(),
        "orchestration": await test_orchestration_service(),
    }
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v is True)
    skipped = sum(1 for v in results.values() if v is None)
    failed = sum(1 for v in results.values() if v is False)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result is True else "⚠️ 跳过" if result is None else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    print(f"\n总计：{passed} 通过，{skipped} 跳过，{failed} 失败")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n🎉 所有测试通过！迁移成功！")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

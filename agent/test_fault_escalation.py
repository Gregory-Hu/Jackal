"""
Fault 检测与 Escalation 测试脚本

演示异常向上汇报机制的工作流程
"""
import asyncio
import os
import shutil
from datetime import datetime


async def test_fault_detection():
    """测试 Fault 检测功能"""
    print("=" * 60)
    print("Fault 检测与 Escalation 测试")
    print("=" * 60)
    
    from infra import (
        FaultDetector,
        FaultReporter,
        EscalationManager,
        detect_faults,
        escalate_fault,
        FaultType,
        FaultSeverity,
    )
    from application import OrchestrationService
    
    # ========== 测试 1: Fault 检测器 ==========
    print("\n[测试 1] Fault 检测器...")
    
    detector = FaultDetector(workspace="./workspace")
    
    # 场景 1: 工作目录不存在
    print("\n  场景 1: 工作目录不存在")
    context = {
        "workspace": "./nonexistent_workspace",
        "task_id": "test_001",
        "agent_id": "test_agent",
    }
    faults = await detector.detect_all(context)
    print(f"  检测到 {len(faults)} 个 Fault")
    for fault in faults:
        print(f"    - {fault.fault_type.value}: {fault.description}")
    
    # 场景 2: 源代码目录不存在
    print("\n  场景 2: 源代码目录不存在")
    os.makedirs("./workspace", exist_ok=True)
    context = {
        "workspace": "./workspace",
        "task_id": "test_002",
        "agent_id": "test_agent",
    }
    faults = await detector.detect_all(context)
    print(f"  检测到 {len(faults)} 个 Fault")
    for fault in faults:
        print(f"    - {fault.fault_type.value}: {fault.description}")
    
    # ========== 测试 2: Fault 报告生成 ==========
    print("\n[测试 2] Fault 报告生成...")
    
    reporter = FaultReporter(faults_dir="./workspace/.faults")
    
    if faults:
        fault = faults[0]
        report = reporter.generate_report(fault, context)
        
        print(f"  生成的 Fault 报告:")
        print(f"    - Fault ID: {report.fault_id}")
        print(f"    - 类型：{report.fault_type}")
        print(f"    - 严重性：{report.severity}")
        print(f"    - 描述：{report.description[:50]}...")
        
        # 保存报告
        file_path = reporter.save_report(report)
        print(f"    - 保存位置：{file_path}")
    
    # ========== 测试 3: Escalation 发送 ==========
    print("\n[测试 3] Escalation 发送...")
    
    manager = EscalationManager()
    
    if faults:
        report = reporter.generate_report(faults[0], context)
        result = await manager.send_escalation(report)
        
        print(f"  Escalation 结果:")
        print(f"    - 通知的接收者：{len(result['notified_recipients'])}")
        print(f"    - SLA: {result['sla_deadline']} 小时")
    
    # ========== 测试 4: Orchestration Service 集成 ==========
    print("\n[测试 4] Orchestration Service 集成...")
    
    orchestrator = OrchestrationService(
        orchestrator_id="test_orchestrator",
    )
    
    # 提交一个任务（会触发 Fault 检测）
    print("\n  提交任务（触发预检检查）...")
    task_id = await orchestrator.submit_task({
        "name": "测试任务",
        "description": "这是一个测试任务，用于验证 Fault 检测",
    })
    print(f"  任务已提交：{task_id}")
    
    # 获取任务计划
    plan = orchestrator.task_plans.get(task_id)
    if plan:
        # 执行计划（会进行 Fault 预检检查）
        print("\n  执行任务计划...")
        result = await orchestrator.execute_plan(plan)
        
        print(f"\n  执行结果:")
        print(f"    - 状态：{result.get('status')}")
        if result.get('status') == 'paused':
            print(f"    - 原因：{result.get('reason')}")
            print(f"    - Faults: {result.get('faults')}")
            print(f"\n  ⏸️  任务已暂停，等待 Human Review...")
            
            # 显示 Fault 报告路径
            print(f"\n  📄 Fault 报告位置:")
            for fault_id in result.get('faults', []):
                print(f"    ./workspace/.faults/{fault_id}.yaml")
    
    # ========== 测试 5: Human Review 模拟 ==========
    print("\n[测试 5] Human Review 模拟...")
    
    # 创建 workspace 目录（模拟 Human 修复）
    print("\n  模拟 Human 修复（创建 workspace 目录）...")
    os.makedirs("./workspace/src", exist_ok=True)
    
    # 创建一个假的源代码文件
    with open("./workspace/src/test.v", "w") as f:
        f.write("// Test RTL file\nmodule test();\nendmodule\n")
    
    print("  ✓ workspace 和 src 目录已创建")
    
    # 解决 Fault
    if faults:
        report = reporter.load_report(faults[0].fault_type.value.replace("MISSING_", "FAULT-2024-"))
        if report:
            print(f"\n  解决 Fault: {report.fault_id}")
            resolved = await orchestrator.resolve_fault(
                fault_id=report.fault_id,
                resolution_description="已创建 workspace 和 src 目录",
                human_id="test_human",
                continue_task=True,
                notes="后续任务请确保目录已预先创建",
            )
            print(f"  Fault 解决状态：{'成功' if resolved else '失败'}")
    
    # ========== 清理 ==========
    print("\n[清理] 清理测试数据...")
    # 不清理，保留 Fault 报告供查看
    # shutil.rmtree("./workspace", ignore_errors=True)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    # 显示 Fault 报告示例
    print("\n📄 Fault 报告示例:")
    faults_dir = "./workspace/.faults"
    if os.path.exists(faults_dir):
        for filename in os.listdir(faults_dir):
            if filename.endswith(".yaml"):
                file_path = os.path.join(faults_dir, filename)
                print(f"\n  文件：{filename}")
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 显示前 10 行
                    lines = content.split("\n")[:10]
                    for line in lines:
                        print(f"    {line}")
                    if len(content.split("\n")) > 10:
                        print("    ...")


if __name__ == "__main__":
    asyncio.run(test_fault_detection())

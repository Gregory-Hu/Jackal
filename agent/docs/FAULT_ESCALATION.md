# 异常向上汇报机制（Fault Detection & Escalation）

## 📋 概述

本系统实现了完整的异常向上汇报机制，当 Agent 在执行任务过程中遇到无法自行解决的问题时，会自动检测到 Fault，生成标准化报告，并触发 Escalation 流程通知 Human Review。

---

## 🏗️ 架构设计

```
┌─────────────────┐
│  Agent 执行任务  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Fault 预检检查  │ ◄── 任务执行前检测
└────────┬────────┘
         │
    ┌────┴────┐
    │  有 Fault? │
    └─┬────┬───┘
      │ No │ Yes
      │    │
      │    ▼
      │ ┌─────────────────┐
      │ │  生成 Fault 报告  │
      │ └────────┬────────┘
      │          │
      │          ▼
      │ ┌─────────────────┐
      │ │  发送 Escalation │
      │ └────────┬────────┘
      │          │
      │          ▼
      │ ┌─────────────────┐
      │ │  等待 Human      │
      │ │  Review & 修复   │
      │ └────────┬────────┘
      │          │
      │          ▼
      │ ┌─────────────────┐
      │ │  验证修复        │
      │ └────────┬────────┘
      │          │
      │     ┌────┴────┐
      │     │ 成功？   │
      │     └─┬────┬───┘
      │       │ No │ Yes
      │       │    │
      │       │    ▼
      │       │ ┌─────────────────┐
      │       │ │  继续执行任务    │
      │       │ └─────────────────┘
      │       │
      │       ▼
      │ ┌─────────────────┐
      └─│  报告失败        │
        └─────────────────┘
```

---

## 📂 文件结构

```
agent/
├── infra/
│   └── fault.py              # Fault 检测与 Escalation 核心实现
├── jd/
│   └── expert_microarch_analyst_resource.md  # JD 资源规范（含 Fault 定义）
├── skills/
│   └── fault_handling_escalation.md  # Fault 处理技能文档
├── application/
│   └── orchestration.py      # Orchestration 服务（集成 Fault 检测）
├── workspace/
│   └── .faults/              # Fault 报告存储目录
│       ├── FAULT-2024-xxx.yaml
│       └── ...
└── test_fault_escalation.py  # 测试脚本
```

---

## 🔍 Fault 类型

### HIGH Severity（需要立即响应）

| Fault ID | 类型 | 描述 | 检测条件 |
|---------|------|------|---------|
| F001 | MISSING_WORKSPACE | 工作目录未配置 | `workspace` 参数为空或目录不存在 |
| F002 | MISSING_SOURCE_CODE | 源代码目录不存在 | `src/` 目录不存在或为空 |
| F003 | MISSING_TOP_LEVEL | 无法定位顶层模块 | 在源码目录中找不到子系统入口 |
| F004 | INSUFFICIENT_ACCESS | 缺少访问权限 | 文件/目录读取或写入失败 |

### MEDIUM Severity（24 小时内响应）

| Fault ID | 类型 | 描述 | 检测条件 |
|---------|------|------|---------|
| F005 | MISSING_JD_RESOURCE | JD 资源未指定 | JD 中缺少必要资源路径 |
| F006 | AMBIGUOUS_SUBSYSTEM | 子系统边界模糊 | 无法确定子系统范围 |
| F007 | CONFLICTING_INFO | 信息冲突 | 不同来源信息不一致 |
| F008 | MISSING_DEPENDENCY | 缺少依赖 | 依赖的模块/文档不存在 |

### LOW Severity（自动处理）

| Fault ID | 类型 | 描述 | 检测条件 |
|---------|------|------|---------|
| F009 | DEPRECATED_REFERENCE | 引用过时 | 引用了已废弃的文件/接口 |
| F010 | INCOMPLETE_DOCUMENTATION | 文档不完整 | 关键文档缺少必要章节 |

---

## 📄 Fault 报告格式

每个 Fault 都会生成标准化的 YAML 报告：

```yaml
fault_id: "FAULT-2024-abc123"
fault_type: "MISSING_SOURCE_CODE"
severity: "HIGH"
status: "detected"  # detected, escalated, under_review, resolved, closed

# 检测信息
detected_by: "expert_microarch_analyst"
detected_at: "2024-01-15T10:30:00Z"
task_id: "task_123"
jd_id: "expert_microarch_analyst"

# 问题描述
description: |
  源代码目录不存在或为空，无法进行微架构分析。
  预期路径：./workspace/src/
  实际状态：目录不存在

# 影响范围
impact:
  - 无法定位子系统顶层模块
  - 无法分析 RTL 代码
  - 任务无法继续执行

# 诊断信息
diagnostics:
  expected: "源代码目录应该存在并包含 RTL 代码"
  actual: "目录不存在"
  workspace: "./workspace"
  current_step: "pre_flight_check"

# 建议修复措施
suggested_fix: |
  1. 确认源代码仓库已正确克隆
  2. 设置 SOURCE_CODE_DIR 环境变量
  3. 或者在任务配置中指定 source_code_dir 参数

# 所需 Human 操作
required_human_action:
  - type: "configuration"
    description: "配置源代码目录路径"
    priority: "HIGH"

# 升级路径
escalation_path:
  - role: "tech_lead"
    notified_at: "2024-01-15T10:30:00Z"

# 解决信息（解决后填写）
resolved_at: "2024-01-15T14:30:00Z"
resolved_by: "human_reviewer"
resolution_description: "已克隆源代码仓库到 ./workspace/src"
human_notes: "后续任务请使用 SOURCE_CODE_DIR=/data/rtl/source"
```

---

## 🔄 工作流程

### 1. Fault 检测（预检检查）

在任务执行前，Orchestration Service 会自动进行预检检查：

```python
from application import OrchestrationService

orchestrator = OrchestrationService()

# 提交任务
task_id = await orchestrator.submit_task({
    "name": "分析 CPU 子系统",
    "description": "分析 CPU 子系统的微架构",
})

# 执行计划（自动进行 Fault 检测）
plan = orchestrator.task_plans[task_id]
result = await orchestrator.execute_plan(plan)

# 如果有 Fault，任务会暂停
if result['status'] == 'paused':
    print(f"任务暂停，等待 Fault 解决：{result['faults']}")
```

### 2. Fault 报告生成

检测到的每个 Fault 都会生成报告并保存到 `./workspace/.faults/` 目录：

```bash
./workspace/.faults/
├── FAULT-2024-abc123.yaml
└── FAULT-2024-def456.yaml
```

### 3. Escalation 发送

系统会自动发送 Escalation 通知给指定的接收者：

```
🔴 [HIGH] Fault FAULT-2024-abc123: MISSING_SOURCE_CODE

源代码目录不存在或为空，无法进行微架构分析。

📋 需要操作:
  - 配置源代码目录路径

📄 查看报告：./workspace/.faults/FAULT-2024-abc123.yaml

⏰ SLA: 4 小时内响应
```

### 4. Human Review & 修复

Human 收到通知后：

1. 查看 Fault 报告
2. 执行修复（如配置目录、提供资源）
3. 调用 API 标记 Fault 已解决

```python
# Human 修复 Fault
resolved = await orchestrator.resolve_fault(
    fault_id="FAULT-2024-abc123",
    resolution_description="已克隆源代码仓库到 ./workspace/src",
    human_id="tech_lead",
    continue_task=True,
    notes="后续任务请使用 SOURCE_CODE_DIR=/data/rtl/source",
)
```

### 5. 验证修复 & 恢复执行

系统会验证 Fault 是否已真正解决：

```python
# 验证修复
fault_report = orchestrator.fault_reporter.load_report("FAULT-2024-abc123")
is_resolved = await orchestrator.handle_fault(fault_report)

if is_resolved:
    print("✅ Fault 已解决，任务继续执行")
else:
    print("⚠️ Fault 验证失败，需要进一步修复")
```

---

## 🛠️ 使用示例

### 示例 1: 检测 MISSING_SOURCE_CODE

```python
from infra import FaultDetector, FaultReporter

# 创建检测器
detector = FaultDetector(workspace="./workspace")

# 检测 Fault
context = {
    "workspace": "./workspace",
    "task_id": "task_001",
    "agent_id": "expert_microarch_analyst",
}

faults = await detector.detect_all(context)

for fault in faults:
    print(f"检测到 Fault: {fault.fault_type.value}")
    print(f"  描述：{fault.description}")
    print(f"  严重性：{fault.severity.value}")
```

### 示例 2: 生成并保存 Fault 报告

```python
from infra import FaultReporter

reporter = FaultReporter(faults_dir="./workspace/.faults")

# 生成报告
report = reporter.generate_report(fault, context)

# 保存报告
file_path = reporter.save_report(report)
print(f"报告已保存：{file_path}")
```

### 示例 3: 发送 Escalation

```python
from infra import EscalationManager

manager = EscalationManager()

# 发送 Escalation
result = await manager.send_escalation(report)

print(f"通知了 {len(result['notified_recipients'])} 个接收者")
print(f"SLA: {result['sla_deadline']} 小时")
```

### 示例 4: Human 解决 Fault

```bash
# 查看 Fault 报告
cat ./workspace/.faults/FAULT-2024-abc123.yaml

# 执行修复（如创建目录）
mkdir -p ./workspace/src
git clone <repo> ./workspace/src

# 标记 Fault 已解决
python -c "
import asyncio
from application import OrchestrationService

async def main():
    orchestrator = OrchestrationService()
    await orchestrator.resolve_fault(
        fault_id='FAULT-2024-abc123',
        resolution_description='已克隆源代码仓库',
        human_id='tech_lead',
        continue_task=True,
    )

asyncio.run(main())
"
```

---

## 📊 Escalation 配置

### escalation_rules.yaml

```yaml
# workspace/.config/escalation_rules.yaml
rules:
  - fault_type: "MISSING_WORKSPACE"
    severity: "HIGH"
    notify:
      - role: "engineering_manager"
        channel: "email"
      - role: "tech_lead"
        channel: "slack"
    sla_hours: 4
    auto_escalate_if_no_response: true
    escalation_timeout_hours: 2
    
  - fault_type: "MISSING_SOURCE_CODE"
    severity: "HIGH"
    notify:
      - role: "tech_lead"
        channel: "slack"
    sla_hours: 4
    
  - fault_type: "AMBIGUOUS_SUBSYSTEM"
    severity: "MEDIUM"
    notify:
      - role: "tech_lead"
        channel: "email"
    sla_hours: 24

# 通知渠道配置
channels:
  email:
    smtp_server: "smtp.example.com"
    from_address: "agent-faults@example.com"
  slack:
    webhook_url: "https://hooks.slack.com/..."
    channel: "#agent-escalations"
```

---

## 🎯 最佳实践

### 1. 预防优于修复

在任务开始前验证所有必要资源：

```python
# 预检检查
context = {
    "workspace": "./workspace",
    "source_code_dir": "./workspace/src",
}

faults = await detector.detect_all(context)
if faults:
    print("⚠️ 检测到 Fault，请先修复后再执行任务")
    for fault in faults:
        print(f"  - {fault.fault_type.value}: {fault.description}")
    return
```

### 2. 快速失败

检测到 Fault 立即上报，不要尝试绕过：

```python
# ❌ 错误：尝试绕过 Fault
if not os.path.exists(src_dir):
    src_dir = "./fallback_dir"  # 不要这样做！

# ✅ 正确：立即上报
if not os.path.exists(src_dir):
    await escalate_fault(report)
    await wait_for_human_review()
```

### 3. 完整上下文

Fault 报告必须包含足够的诊断信息：

```yaml
# ✅ 好的报告
diagnostics:
  expected: "源代码目录应该存在并包含 RTL 代码"
  actual: "目录不存在"
  workspace: "./workspace"
  current_step: "pre_flight_check"

# ❌ 差的报告
diagnostics:
  error: "目录不存在"  # 缺少上下文
```

### 4. 可追溯性

所有 Fault 和修复都必须记录在案：

```bash
# 查看 Fault 历史
ls -la ./workspace/.faults/

# 分析 Fault 模式
python analyze_faults.py
```

### 5. 持续改进

定期回顾 Fault 模式，优化检测和预防：

```python
# 从 Fault 中学习
async def learn_from_fault(report: FaultReport):
    # 提取学习点
    learning = {
        "fault_type": report.fault_type,
        "pattern": report.diagnostics.actual,
        "solution": report.resolution_description,
        "prevention": report.suggested_fix,
    }
    
    # 添加到知识库
    await memory.store_knowledge(
        key=f"fault_pattern:{report.fault_type}",
        value=learning,
        tags=["fault", "learning"],
    )
```

---

## 🧪 测试

运行测试脚本验证 Fault 检测和 Escalation 功能：

```bash
python test_fault_escalation.py
```

测试场景包括：
1. 工作目录不存在
2. 源代码目录不存在
3. Fault 报告生成
4. Escalation 发送
5. Human Review 模拟
6. Fault 验证和恢复

---

## 📚 相关文档

- [JD 资源规范](jd/expert_microarch_analyst_resource.md) - Fault 定义和目录规范
- [Fault 处理技能](skills/fault_handling_escalation.md) - 详细的技能文档
- [Orchestration 服务](application/orchestration.py) - 集成实现

---

## 🔗 总结

异常向上汇报机制确保 Agent 在遇到问题时能够：
1. ✅ **自动检测** Fault
2. ✅ **生成标准化报告**
3. ✅ **触发 Escalation** 通知 Human
4. ✅ **等待 Review** 并验证修复
5. ✅ **恢复执行** 任务

这使得系统具有**可追溯性**、**可审计性**和**可靠性**，适合企业级生产环境使用。

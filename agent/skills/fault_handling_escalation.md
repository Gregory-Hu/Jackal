---
skill_set_id: fault_handling_escalation
role: all
name: 异常检测与向上汇报技能（Fault Detection & Escalation）
description: |
  检测和报告任务执行过程中的异常情况，
  触发向上汇报流程，等待 Human Review 后恢复执行。
---

# 异常检测与向上汇报技能（Fault Detection & Escalation）

## 技能目标

本技能使 Agent 能够：
1. 识别任务执行过程中的各类 Fault
2. 生成标准化的 Fault 报告
3. 触发 Escalation 流程通知 Human
4. 等待 Human Review 并验证修复
5. 从 Fault 中学习并更新知识库

---

## Fault 类型定义

### HIGH Severity

| Fault ID | 类型 | 描述 | 检测条件 |
|---------|------|------|---------|
| F001 | MISSING_WORKSPACE | 工作目录未配置 | `workspace` 参数为空或目录不存在 |
| F002 | MISSING_SOURCE_CODE | 源代码目录不存在 | `src/` 目录不存在或为空 |
| F003 | MISSING_TOP_LEVEL | 无法定位顶层模块 | 在源码目录中找不到子系统入口 |
| F004 | INSUFFICIENT_ACCESS | 缺少访问权限 | 文件/目录读取失败 |

### MEDIUM Severity

| Fault ID | 类型 | 描述 | 检测条件 |
|---------|------|------|---------|
| F005 | MISSING_JD_RESOURCE | JD 资源未指定 | JD 中缺少必要资源路径 |
| F006 | AMBIGUOUS_SUBSYSTEM | 子系统边界模糊 | 无法确定子系统范围 |
| F007 | CONFLICTING_INFO | 信息冲突 | 不同来源信息不一致 |
| F008 | MISSING_DEPENDENCY | 缺少依赖 | 依赖的模块/文档不存在 |

### LOW Severity

| Fault ID | 类型 | 描述 | 检测条件 |
|---------|------|------|---------|
| F009 | DEPRECATED_REFERENCE | 引用过时 | 引用了已废弃的文件/接口 |
| F010 | INCOMPLETE_DOCUMENTATION | 文档不完整 | 关键文档缺少必要章节 |

---

## Fault 检测流程

```python
async def detect_faults(context: TaskContext) -> List[Fault]:
    """检测当前任务上下文中的 Fault"""
    faults = []
    
    # 1. 检查工作目录
    if not context.workspace or not os.path.exists(context.workspace):
        faults.append(Fault(
            fault_id=generate_fault_id(),
            fault_type="MISSING_WORKSPACE",
            severity="HIGH",
            description="工作目录未配置或不存在",
            context=context,
        ))
    
    # 2. 检查源代码目录
    src_dir = context.source_code_dir or os.path.join(context.workspace, "src")
    if not os.path.exists(src_dir) or not os.listdir(src_dir):
        faults.append(Fault(
            fault_id=generate_fault_id(),
            fault_type="MISSING_SOURCE_CODE",
            severity="HIGH",
            description="源代码目录不存在或为空",
            context=context,
        ))
    
    # 3. 检查 JD 资源
    if context.jd and not context.jd.resources:
        faults.append(Fault(
            fault_id=generate_fault_id(),
            fault_type="MISSING_JD_RESOURCE",
            severity="MEDIUM",
            description="JD 中未指定必要资源路径",
            context=context,
        ))
    
    # 4. 检查顶层模块
    if not await find_top_level_module(src_dir, context.subsystem):
        faults.append(Fault(
            fault_id=generate_fault_id(),
            fault_type="MISSING_TOP_LEVEL",
            severity="HIGH",
            description="无法定位子系统顶层模块",
            context=context,
        ))
    
    return faults
```

---

## Fault 报告生成

### 报告结构

```yaml
fault_id: "FAULT-{YYYY}-{NNN}"
fault_type: "{FAULT_TYPE}"
severity: "HIGH|MEDIUM|LOW"
status: "DETECTED|ESCALATED|UNDER_REVIEW|RESOLVED|CLOSED"

# 检测信息
detected_by: "{agent_id}"
detected_at: "{ISO8601_timestamp}"
task_id: "{task_id}"
jd_id: "{jd_id}"

# 问题描述
description: |
  详细的问题描述...

# 影响范围
impact:
  - "影响项 1"
  - "影响项 2"

# 诊断信息
diagnostics:
  expected: "期望的状态或配置"
  actual: "实际检测到的状态"
  workspace: "./workspace"
  current_step: "当前执行步骤"

# 建议修复措施
suggested_fix: |
  1. 第一步...
  2. 第二步...

# 所需 Human 操作
required_human_action:
  - type: "configuration|resource|decision|other"
    description: "需要 Human 执行的操作"
    priority: "HIGH|MEDIUM|LOW"
    deadline: "可选的截止时间"

# 升级路径
escalation_path:
  - role: "tech_lead"
    notified_at: "{timestamp}"
  - role: "engineering_manager"
    notified_at: "{timestamp}"

# 解决信息（解决后填写）
resolved_at: "{ISO8601_timestamp}"
resolved_by: "{human_id}"
resolution_description: "如何解决的描述"
```

### 生成函数

```python
def generate_fault_report(
    fault: Fault,
    context: TaskContext,
) -> FaultReport:
    """生成 Fault 报告"""
    return FaultReport(
        fault_id=generate_fault_id(),
        fault_type=fault.fault_type,
        severity=fault.severity,
        status="DETECTED",
        detected_by=context.agent_id,
        detected_at=datetime.now().isoformat(),
        task_id=context.task_id,
        jd_id=context.jd_id,
        description=fault.description,
        impact=fault.impact,
        diagnostics={
            "expected": fault.expected_state,
            "actual": fault.actual_state,
            "workspace": context.workspace,
            "current_step": context.current_step,
        },
        suggested_fix=fault.suggested_fix,
        required_human_action=fault.required_actions,
    )
```

---

## Escalation 流程

### 发送 Escalation 通知

```python
async def send_escalation(
    report: FaultReport,
    escalation_config: EscalationConfig,
) -> EscalationResult:
    """发送 Escalation 通知"""
    
    # 根据严重性确定接收者
    recipients = determine_recipients(report.severity, escalation_config)
    
    # 构建通知消息
    notification = EscalationNotification(
        fault_id=report.fault_id,
        fault_type=report.fault_type,
        severity=report.severity,
        description=report.description,
        required_action=report.required_human_action,
        fault_report_path=f"./workspace/.faults/{report.fault_id}.yaml",
        sla_hours=get_sla_hours(report.severity),
    )
    
    # 发送通知
    results = []
    for recipient in recipients:
        result = await notify_recipient(recipient, notification)
        results.append(result)
    
    # 保存 Fault 报告
    save_fault_report(report, f"./workspace/.faults/{report.fault_id}.yaml")
    
    return EscalationResult(
        fault_id=report.fault_id,
        notified_recipients=recipients,
        notification_results=results,
        escalated_at=datetime.now().isoformat(),
    )
```

### Escalation 配置

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

## Human Review 流程

### Human 操作界面

当 Human 收到 Escalation 通知后，可以通过以下方式响应：

1. **查看 Fault 报告**
   ```bash
   cat ./workspace/.faults/FAULT-2024-001.yaml
   ```

2. **执行修复**
   - 配置缺失的目录
   - 提供缺失的资源
   - 澄清模糊的信息

3. **标记已修复**
   ```bash
   # 更新 Fault 状态
   agent-cli resolve-fault FAULT-2024-001 \
     --resolution "配置了正确的源代码目录" \
     --continue-task
   ```

4. **提供额外说明**（可选）
   ```yaml
   # 添加到 Fault 报告
   human_notes: |
     源代码位于 /data/rtl/source，已在配置文件中更新。
     后续类似任务请优先检查 SOURCE_CODE_DIR 环境变量。
   ```

### Review 响应处理

```python
async def handle_human_review(
    fault_id: str,
    review: HumanReview,
) -> ReviewResult:
    """处理 Human Review 响应"""
    
    # 更新 Fault 状态
    report = load_fault_report(fault_id)
    report.status = "RESOLVED"
    report.resolved_at = datetime.now().isoformat()
    report.resolved_by = review.human_id
    report.resolution_description = review.resolution_description
    report.human_notes = review.notes
    
    save_fault_report(report)
    
    # 验证修复
    verification = await verify_fix(report)
    if not verification.success:
        report.status = "VERIFICATION_FAILED"
        save_fault_report(report)
        return ReviewResult(
            success=False,
            message=f"修复验证失败：{verification.error}",
        )
    
    # 恢复任务执行
    if review.continue_task:
        await resume_task(report.task_id)
        return ReviewResult(
            success=True,
            message="Fault 已解决，任务已恢复执行",
        )
    
    return ReviewResult(
        success=True,
        message="Fault 已解决，任务保持暂停",
    )
```

---

## Fault 恢复与学习

### 恢复执行

```python
async def resume_after_fault(
    task_id: str,
    fault_report: FaultReport,
) -> ResumeResult:
    """Fault 解决后恢复任务执行"""
    
    # 从 Fault 点恢复
    task = get_task(task_id)
    task.status = "RUNNING"
    task.current_step = fault_report.context.current_step
    
    # 更新上下文
    task.context.faults_resolved.append(fault_report.fault_id)
    task.context.last_fault_resolution = fault_report.resolution_description
    
    # 继续执行
    result = await execute_task_step(task)
    
    return ResumeResult(
        task_id=task_id,
        resumed_at=datetime.now().isoformat(),
        next_step=result.next_step,
    )
```

### 经验学习

```python
async def learn_from_fault(
    fault_report: FaultReport,
) -> LearningEntry:
    """从 Fault 中学习并更新知识库"""
    
    # 提取学习点
    learning = LearningEntry(
        id=generate_learning_id(),
        fault_type=fault_report.fault_type,
        pattern=fault_report.diagnostics.actual,
        solution=fault_report.resolution_description,
        prevention=fault_report.suggested_fix,
        created_at=datetime.now().isoformat(),
    )
    
    # 添加到知识库
    await memory.store_knowledge(
        key=f"fault_pattern:{fault_report.fault_type}",
        value=learning.to_dict(),
        tags=["fault", "learning", fault_report.fault_type],
    )
    
    # 更新检测规则
    await update_fault_detection_rules(fault_report)
    
    return learning
```

---

## 使用示例

### 示例 1: 检测 MISSING_SOURCE_CODE

```python
# Agent 执行任务
context = TaskContext(
    task_id="task_123",
    jd_id="expert_microarch_analyst",
    workspace="./workspace",
    subsystem="cpu_core",
)

# 检测 Fault
faults = await detect_faults(context)

# 发现 Fault
if faults:
    fault = faults[0]  # MISSING_SOURCE_CODE
    
    # 生成报告
    report = generate_fault_report(fault, context)
    
    # 发送 Escalation
    escalation = await send_escalation(report, escalation_config)
    
    # 等待 Human Review
    print(f"Fault 已上报：{report.fault_id}")
    print(f"等待 Human Review...")
    
    # 进入等待状态
    await wait_for_human_review(report.fault_id)
```

### 示例 2: Human Review 响应

```bash
# Human 收到通知
# Slack 消息：
# [HIGH] Fault FAULT-2024-001: MISSING_SOURCE_CODE
# 需要操作：配置源代码目录路径
# 查看报告：./workspace/.faults/FAULT-2024-001.yaml

# Human 执行修复
mkdir -p ./workspace/src
cp -r /path/to/rtl/source/* ./workspace/src/

# Human 标记已修复
agent-cli resolve-fault FAULT-2024-001 \
  --resolution "已克隆源代码仓库到 ./workspace/src" \
  --continue-task \
  --notes "后续任务请使用 SOURCE_CODE_DIR=/data/rtl/source"

# Agent 恢复执行
# Fault 已解决，任务继续...
```

---

## 最佳实践

1. **预防优于修复**
   - 在任务开始前验证所有必要资源
   - 使用预检检查（pre-flight check）

2. **快速失败**
   - 检测到 Fault 立即上报
   - 不要尝试绕过或隐藏 Fault

3. **完整上下文**
   - Fault 报告必须包含足够的诊断信息
   - 包括期望状态和实际状态的对比

4. **可追溯性**
   - 所有 Fault 和修复都必须记录
   - 保存 Fault 历史用于分析

5. **持续改进**
   - 定期回顾 Fault 模式
   - 优化检测和预防规则
   - 将常见 Fault 的解决方案自动化

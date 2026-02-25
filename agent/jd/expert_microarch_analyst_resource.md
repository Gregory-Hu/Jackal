## 工程资源与目录规范（Resource & Directory Convention）

为保证子系统微架构分析工作的可追溯性、一致性与可扩展性，
Expert Agent 需要在统一的工程目录结构下组织、引用和产出分析材料。

---

### 1. Resource Directory
- 用于存放分析过程中产生或引用的中间资源
- 资源包括但不限于：
  - 架构草图
  - 接口抽象描述
  - 跨模块机制讨论材料
- 资源需具备清晰命名和来源说明

> **默认路径**: `./workspace/resources/`

---

### 2. Source Code Directory
- 用于引用和定位被分析的 RTL / 源代码
- 要求：
  - 明确子系统顶层入口
  - 模块级代码可快速定位
- 不要求对源码做修改，仅作为分析输入使用

> **默认路径**: `./workspace/src/` 或环境变量 `SOURCE_CODE_DIR` 指定

---

### 3. Documentation Directory
- 用于存放分析产出与工程知识沉淀
- 文档类型包括但不限于：
  - 子系统概述
  - 模块级分析总结
  - 系统级工程知识归纳
- 所有系统级结论必须有对应文档承载

> **默认路径**: `./workspace/docs/`

---

### 4. Fault Detection & Escalation（异常检测与汇报）

#### 4.1 Fault 定义

在微架构分析过程中，以下情况被定义为 **Fault**，需要向上汇报：

| Fault 类型 | 描述 | 严重性 |
|-----------|------|--------|
| **MISSING_WORKSPACE** | 工作目录未配置或不存在 | HIGH |
| **MISSING_SOURCE_CODE** | 源代码目录不存在或为空 | HIGH |
| **MISSING_JD_RESOURCE** | JD 中未指定必要资源路径 | MEDIUM |
| **AMBIGUOUS_SUBSYSTEM** | 子系统边界/入口不明确 | MEDIUM |
| **MISSING_TOP_LEVEL** | 无法定位子系统顶层模块 | HIGH |
| **CONFLICTING_INFO** | 不同来源信息冲突 | MEDIUM |
| **INSUFFICIENT_ACCESS** | 缺少必要文件访问权限 | HIGH |

#### 4.2 Fault 处理流程

```
┌─────────────────┐
│  Agent 执行任务  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  检测 Fault      │
└────────┬────────┘
         │
    ┌────┴────┐
    │  有 Fault? │
    └─┬────┬───┘
      │ No │ Yes
      │    │
      │    ▼
      │ ┌─────────────────┐
      │ │  创建 Fault 报告  │
      │ └────────┬────────┘
      │          │
      │          ▼
      │ ┌─────────────────┐
      │ │  触发 Escalation │
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
      └─│  继续执行任务    │
        └─────────────────┘
```

#### 4.3 Fault 报告格式

当检测到 Fault 时，Agent 必须生成以下格式的报告：

```yaml
fault_id: "FAULT-2024-001"
fault_type: "MISSING_SOURCE_CODE"
severity: "HIGH"
detected_by: "expert_microarch_analyst"
detected_at: "2024-01-15T10:30:00Z"

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

# 建议修复措施
suggested_fix: |
  1. 确认源代码仓库已正确克隆
  2. 设置 SOURCE_CODE_DIR 环境变量指向正确的路径
  3. 或者在任务配置中明确指定 source_code_dir 参数

# 所需 Human 操作
required_human_action:
  - type: "configuration"
    description: "配置源代码目录路径"
    priority: "HIGH"
    
# 上下文信息
context:
  jd_id: "expert_microarch_analyst"
  task_id: "task_123"
  workspace: "./workspace"
  current_step: "source_code_analysis"
```

#### 4.4 Escalation 接收者

根据 Fault 类型和严重性，Escalation 会发送给不同的接收者：

| Fault 严重性 | 接收者 | 响应 SLA |
|-------------|--------|---------|
| **HIGH** | Engineering Manager + Tech Lead | 4 小时 |
| **MEDIUM** | Tech Lead | 24 小时 |
| **LOW** | Senior Agent (自动处理) | 自动 |

#### 4.5 Agent 行为准则

当检测到 Fault 时，Agent 应该：

1. **立即停止** 当前任务的执行
2. **生成 Fault 报告** 并保存到 `./workspace/.faults/{fault_id}.yaml`
3. **发送 Escalation 消息** 给指定的接收者
4. **进入等待状态**，直到 Human Review 完成
5. **恢复执行** 当 Fault 被修复并收到继续指令

当 Fault 被修复后，Agent 应该：

1. **验证修复** 确认问题已解决
2. **更新 Fault 状态** 标记为 `RESOLVED`
3. **记录经验** 将 Fault 和解决方案添加到知识库
4. **继续执行** 从暂停点恢复任务

---

### 5. 默认目录结构

```
workspace/
├── .faults/                    # Fault 报告目录
│   ├── FAULT-2024-001.yaml
│   └── FAULT-2024-002.yaml
├── resources/                  # 分析资源
│   ├── diagrams/
│   ├── interfaces/
│   └── discussions/
├── src/                        # 源代码（或 symlink）
│   ├── subsystem_a/
│   ├── subsystem_b/
│   └── top_level/
├── docs/                       # 分析文档
│   ├── subsystem_overview/
│   ├── module_analysis/
│   └── system_knowledge/
└── .config/                    # 配置文件
    ├── workspace_config.yaml
    └── escalation_rules.yaml
```

---

### 6. 配置示例

#### 6.1 Workspace 配置 (`workspace/.config/workspace_config.yaml`)

```yaml
workspace_version: "1.0"
created_at: "2024-01-15"

# 目录配置
directories:
  resources: "./resources"
  source_code: "./src"
  documentation: "./docs"
  faults: "./.faults"

# 可选：覆盖默认路径
overrides:
  source_code_dir: "/path/to/rtl/source"  # 如果不在 workspace 内

# Escalation 配置
escalation:
  default_reviewer: "tech_lead@example.com"
  high_severity_reviewer: "engineering_manager@example.com"
  auto_resolve_low_severity: true
```

#### 6.2 Escalation 规则 (`workspace/.config/escalation_rules.yaml`)

```yaml
rules:
  - fault_type: "MISSING_WORKSPACE"
    severity: "HIGH"
    notify:
      - role: "engineering_manager"
      - role: "tech_lead"
    sla_hours: 4
    
  - fault_type: "MISSING_SOURCE_CODE"
    severity: "HIGH"
    notify:
      - role: "tech_lead"
    sla_hours: 4
    
  - fault_type: "MISSING_JD_RESOURCE"
    severity: "MEDIUM"
    notify:
      - role: "tech_lead"
    sla_hours: 24
    
  - fault_type: "AMBIGUOUS_SUBSYSTEM"
    severity: "MEDIUM"
    notify:
      - role: "tech_lead"
    sla_hours: 24

# 自动处理规则
auto_resolve:
  enabled: true
  fault_types:
    - "LOW_SEVERITY_CONFIG_ISSUE"
  max_attempts: 3
```

---

### 7. Human Review 流程

当 Human 收到 Escalation 后：

1. **查看 Fault 报告** 在 `./workspace/.faults/{fault_id}.yaml`
2. **评估影响** 确定影响范围和优先级
3. **执行修复** 如配置目录、提供缺失资源等
4. **标记已修复** 更新 Fault 状态为 `RESOLVED`
5. **通知 Agent** 发送继续执行指令
6. **验证恢复** 确认 Agent 可以继续执行

---

### 8. 最佳实践

1. **预防优于修复**: 在任务开始前验证所有必要资源
2. **快速失败**: 检测到 Fault 立即上报，不要尝试绕过
3. **完整上下文**: Fault 报告必须包含足够的上下文信息
4. **可追溯性**: 所有 Fault 和修复都必须记录在案
5. **持续改进**: 定期回顾 Fault 模式，优化检测和预防

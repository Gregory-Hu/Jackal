"""
Fault 检测与 Escalation 模块

实现异常检测、报告生成、向上汇报和 Human Review 流程
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import yaml
import os
import json


class FaultSeverity(Enum):
    """Fault 严重性"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FaultStatus(Enum):
    """Fault 状态"""
    DETECTED = "detected"
    ESCALATED = "escalated"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    CLOSED = "closed"
    VERIFICATION_FAILED = "verification_failed"


class FaultType(Enum):
    """Fault 类型"""
    # HIGH Severity
    MISSING_WORKSPACE = "MISSING_WORKSPACE"
    MISSING_SOURCE_CODE = "MISSING_SOURCE_CODE"
    MISSING_TOP_LEVEL = "MISSING_TOP_LEVEL"
    INSUFFICIENT_ACCESS = "INSUFFICIENT_ACCESS"
    
    # MEDIUM Severity
    MISSING_JD_RESOURCE = "MISSING_JD_RESOURCE"
    AMBIGUOUS_SUBSYSTEM = "AMBIGUOUS_SUBSYSTEM"
    CONFLICTING_INFO = "CONFLICTING_INFO"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    
    # LOW Severity
    DEPRECATED_REFERENCE = "DEPRECATED_REFERENCE"
    INCOMPLETE_DOCUMENTATION = "INCOMPLETE_DOCUMENTATION"


@dataclass
class Fault:
    """
    Fault 定义
    
    表示检测到的异常
    """
    fault_type: FaultType
    severity: FaultSeverity
    description: str
    
    # 诊断信息
    expected_state: str = ""
    actual_state: str = ""
    
    # 影响范围
    impact: List[str] = field(default_factory=list)
    
    # 建议修复措施
    suggested_fix: str = ""
    
    # 所需 Human 操作
    required_actions: List[Dict[str, Any]] = field(default_factory=list)
    
    # 上下文
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FaultReport:
    """
    Fault 报告
    
    标准化的 Fault 文档
    """
    fault_id: str
    fault_type: str
    severity: str
    status: str = "detected"
    
    # 检测信息
    detected_by: str = ""
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    task_id: str = ""
    jd_id: str = ""
    
    # 问题描述
    description: str = ""
    
    # 影响范围
    impact: List[str] = field(default_factory=list)
    
    # 诊断信息
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    
    # 建议修复措施
    suggested_fix: str = ""
    
    # 所需 Human 操作
    required_human_action: List[Dict[str, Any]] = field(default_factory=list)
    
    # 升级路径
    escalation_path: List[Dict[str, str]] = field(default_factory=list)
    
    # 解决信息
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_description: Optional[str] = None
    human_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "fault_id": self.fault_id,
            "fault_type": self.fault_type,
            "severity": self.severity,
            "status": self.status,
            "detected_by": self.detected_by,
            "detected_at": self.detected_at,
            "task_id": self.task_id,
            "jd_id": self.jd_id,
            "description": self.description,
            "impact": self.impact,
            "diagnostics": self.diagnostics,
            "suggested_fix": self.suggested_fix,
            "required_human_action": self.required_human_action,
            "escalation_path": self.escalation_path,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
            "resolution_description": self.resolution_description,
            "human_notes": self.human_notes,
        }
    
    def to_yaml(self) -> str:
        """转换为 YAML 格式"""
        return yaml.dump(self.to_dict(), allow_unicode=True, default_flow_style=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FaultReport":
        """从字典创建"""
        return cls(
            fault_id=data.get("fault_id", ""),
            fault_type=data.get("fault_type", ""),
            severity=data.get("severity", ""),
            status=data.get("status", "detected"),
            detected_by=data.get("detected_by", ""),
            detected_at=data.get("detected_at", ""),
            task_id=data.get("task_id", ""),
            jd_id=data.get("jd_id", ""),
            description=data.get("description", ""),
            impact=data.get("impact", []),
            diagnostics=data.get("diagnostics", {}),
            suggested_fix=data.get("suggested_fix", ""),
            required_human_action=data.get("required_human_action", []),
            escalation_path=data.get("escalation_path", []),
            resolved_at=data.get("resolved_at"),
            resolved_by=data.get("resolved_by"),
            resolution_description=data.get("resolution_description"),
            human_notes=data.get("human_notes"),
        )


@dataclass
class EscalationNotification:
    """Escalation 通知"""
    fault_id: str
    fault_type: str
    severity: str
    description: str
    required_action: List[Dict[str, Any]]
    fault_report_path: str
    sla_hours: int
    
    def to_message(self) -> str:
        """生成通知消息"""
        emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(self.severity, "⚪")
        return f"""
{emoji} [{self.severity}] Fault {self.fault_id}: {self.fault_type}

{self.description}

📋 需要操作:
{chr(10).join(f"  - {a.get('description', 'N/A')}" for a in self.required_action)}

📄 查看报告：{self.fault_report_path}

⏰ SLA: {self.sla_hours} 小时内响应
        """.strip()


@dataclass
class HumanReview:
    """Human Review 响应"""
    human_id: str
    fault_id: str
    resolution_description: str
    continue_task: bool = True
    notes: Optional[str] = None


class FaultDetector:
    """
    Fault 检测器
    
    检测任务执行过程中的各类 Fault
    """
    
    def __init__(self, workspace: str = "./workspace"):
        self.workspace = workspace
    
    async def detect_all(self, context: Dict[str, Any]) -> List[Fault]:
        """检测所有 Fault"""
        faults = []
        
        # 1. 检查工作目录
        fault = self._check_workspace(context)
        if fault:
            faults.append(fault)
        
        # 2. 检查源代码目录
        fault = self._check_source_code(context)
        if fault:
            faults.append(fault)
        
        # 3. 检查 JD 资源
        fault = self._check_jd_resources(context)
        if fault:
            faults.append(fault)
        
        # 4. 检查访问权限
        fault = self._check_access_permissions(context)
        if fault:
            faults.append(fault)
        
        return faults
    
    def _check_workspace(self, context: Dict[str, Any]) -> Optional[Fault]:
        """检查工作目录"""
        workspace = context.get("workspace", self.workspace)
        
        if not workspace:
            return Fault(
                fault_type=FaultType.MISSING_WORKSPACE,
                severity=FaultSeverity.HIGH,
                description="工作目录未配置",
                expected_state="工作目录应该是一个有效的路径",
                actual_state="workspace 参数为空",
                impact=[
                    "无法存储分析资源",
                    "无法保存分析文档",
                    "任务无法继续执行",
                ],
                suggested_fix="""
1. 在任务配置中设置 workspace 参数
2. 或者设置 WORKSPACE_DIR 环境变量
3. 确保目录存在且有写入权限
                """.strip(),
                required_actions=[
                    {
                        "type": "configuration",
                        "description": "配置工作目录路径",
                        "priority": "HIGH",
                    }
                ],
                context=context,
            )
        
        if not os.path.exists(workspace):
            return Fault(
                fault_type=FaultType.MISSING_WORKSPACE,
                severity=FaultSeverity.HIGH,
                description=f"工作目录不存在：{workspace}",
                expected_state=f"目录 {workspace} 应该存在",
                actual_state="目录不存在",
                impact=[
                    "无法存储分析资源",
                    "无法保存分析文档",
                ],
                suggested_fix=f"""
1. 创建目录：mkdir -p {workspace}
2. 或者修改 workspace 配置指向现有目录
                """.strip(),
                required_actions=[
                    {
                        "type": "resource",
                        "description": f"创建工作目录 {workspace}",
                        "priority": "HIGH",
                    }
                ],
                context=context,
            )
        
        return None
    
    def _check_source_code(self, context: Dict[str, Any]) -> Optional[Fault]:
        """检查源代码目录"""
        workspace = context.get("workspace", self.workspace)
        src_dir = context.get("source_code_dir") or os.path.join(workspace, "src")
        
        if not os.path.exists(src_dir):
            return Fault(
                fault_type=FaultType.MISSING_SOURCE_CODE,
                severity=FaultSeverity.HIGH,
                description=f"源代码目录不存在：{src_dir}",
                expected_state="源代码目录应该存在并包含 RTL 代码",
                actual_state="目录不存在",
                impact=[
                    "无法定位子系统顶层模块",
                    "无法分析 RTL 代码",
                    "任务无法继续执行",
                ],
                suggested_fix=f"""
1. 确认源代码仓库已正确克隆
2. 设置 SOURCE_CODE_DIR 环境变量
3. 或者在任务配置中指定 source_code_dir 参数
4. 确保目录包含子系统代码
                """.strip(),
                required_actions=[
                    {
                        "type": "resource",
                        "description": "配置源代码目录路径",
                        "priority": "HIGH",
                    }
                ],
                context=context,
            )
        
        # 检查目录是否为空
        if os.path.isdir(src_dir) and not os.listdir(src_dir):
            return Fault(
                fault_type=FaultType.MISSING_SOURCE_CODE,
                severity=FaultSeverity.HIGH,
                description=f"源代码目录为空：{src_dir}",
                expected_state="源代码目录应该包含 RTL 代码文件",
                actual_state="目录存在但为空",
                impact=[
                    "无法进行代码分析",
                ],
                suggested_fix=f"""
1. 克隆源代码仓库到 {src_dir}
2. 或者修改 source_code_dir 配置指向正确的路径
                """.strip(),
                required_actions=[
                    {
                        "type": "resource",
                        "description": "填充源代码目录",
                        "priority": "HIGH",
                    }
                ],
                context=context,
            )
        
        return None
    
    def _check_jd_resources(self, context: Dict[str, Any]) -> Optional[Fault]:
        """检查 JD 资源"""
        jd = context.get("jd")
        
        if jd and not getattr(jd, "resources", None):
            return Fault(
                fault_type=FaultType.MISSING_JD_RESOURCE,
                severity=FaultSeverity.MEDIUM,
                description="JD 中未指定必要资源路径",
                expected_state="JD 应该包含资源目录配置",
                actual_state="JD 缺少 resources 字段",
                impact=[
                    "可能无法访问必要的分析资源",
                ],
                suggested_fix="""
1. 在 JD 中添加 resources 字段
2. 或者在任务配置中提供资源路径
                """.strip(),
                required_actions=[
                    {
                        "type": "configuration",
                        "description": "在 JD 中配置资源路径",
                        "priority": "MEDIUM",
                    }
                ],
                context=context,
            )
        
        return None
    
    def _check_access_permissions(self, context: Dict[str, Any]) -> Optional[Fault]:
        """检查访问权限"""
        workspace = context.get("workspace", self.workspace)
        
        if workspace and os.path.exists(workspace):
            # 检查写权限
            test_file = os.path.join(workspace, f".test_{uuid.uuid4().hex[:8]}")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
            except PermissionError:
                return Fault(
                    fault_type=FaultType.INSUFFICIENT_ACCESS,
                    severity=FaultSeverity.HIGH,
                    description=f"缺少工作目录写权限：{workspace}",
                    expected_state="对工作目录有读写权限",
                    actual_state="写权限不足",
                    impact=[
                        "无法保存分析结果",
                        "无法创建 Fault 报告",
                    ],
                    suggested_fix=f"""
1. 修改目录权限：chmod u+w {workspace}
2. 或者使用有权限的目录
3. 检查文件所有者：chown $USER:$USER {workspace}
                    """.strip(),
                    required_actions=[
                        {
                            "type": "configuration",
                            "description": "修复目录权限",
                            "priority": "HIGH",
                        }
                    ],
                    context=context,
                )
        
        return None


class FaultReporter:
    """
    Fault 报告器
    
    生成和管理 Fault 报告
    """
    
    def __init__(self, faults_dir: str = "./workspace/.faults"):
        self.faults_dir = faults_dir
        os.makedirs(faults_dir, exist_ok=True)
    
    def generate_report(
        self,
        fault: Fault,
        context: Dict[str, Any],
    ) -> FaultReport:
        """生成 Fault 报告"""
        return FaultReport(
            fault_id=self._generate_fault_id(),
            fault_type=fault.fault_type.value,
            severity=fault.severity.value,
            status="detected",
            detected_by=context.get("agent_id", "unknown"),
            task_id=context.get("task_id", ""),
            jd_id=context.get("jd_id", ""),
            description=fault.description,
            impact=fault.impact,
            diagnostics={
                "expected": fault.expected_state,
                "actual": fault.actual_state,
                "workspace": context.get("workspace", ""),
                "current_step": context.get("current_step", ""),
            },
            suggested_fix=fault.suggested_fix,
            required_human_action=fault.required_actions,
        )
    
    def save_report(self, report: FaultReport) -> str:
        """保存 Fault 报告到文件"""
        file_path = os.path.join(self.faults_dir, f"{report.fault_id}.yaml")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report.to_yaml())
        
        return file_path
    
    def load_report(self, fault_id: str) -> Optional[FaultReport]:
        """加载 Fault 报告"""
        file_path = os.path.join(self.faults_dir, f"{fault_id}.yaml")
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        return FaultReport.from_dict(data)
    
    def update_report(self, report: FaultReport) -> str:
        """更新 Fault 报告"""
        return self.save_report(report)
    
    def _generate_fault_id(self) -> str:
        """生成 Fault ID"""
        year = datetime.now().year
        # 简单实现，实际应该从存储中获取下一个序号
        unique_id = uuid.uuid4().hex[:6]
        return f"FAULT-{year}-{unique_id}"


class EscalationManager:
    """
    Escalation 管理器
    
    管理向上汇报流程
    """
    
    def __init__(self, config_path: str = "./workspace/.config/escalation_rules.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载 Escalation 配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def determine_recipients(
        self,
        severity: str,
        fault_type: str,
    ) -> List[Dict[str, str]]:
        """根据严重性确定通知接收者"""
        rules = self.config.get("rules", [])
        
        # 查找匹配的规则
        for rule in rules:
            if rule.get("fault_type") == fault_type or rule.get("severity") == severity:
                return rule.get("notify", [])
        
        # 默认接收者
        if severity == "HIGH":
            return [
                {"role": "engineering_manager", "channel": "email"},
                {"role": "tech_lead", "channel": "slack"},
            ]
        elif severity == "MEDIUM":
            return [
                {"role": "tech_lead", "channel": "email"},
            ]
        else:
            return [
                {"role": "senior_agent", "channel": "internal"},
            ]
    
    def get_sla_hours(self, severity: str) -> int:
        """获取 SLA 响应时间（小时）"""
        sla_map = {
            "HIGH": 4,
            "MEDIUM": 24,
            "LOW": 72,
        }
        return sla_map.get(severity, 24)
    
    async def send_escalation(
        self,
        report: FaultReport,
    ) -> Dict[str, Any]:
        """发送 Escalation 通知"""
        recipients = self.determine_recipients(report.severity, report.fault_type)
        sla_hours = self.get_sla_hours(report.severity)
        
        notification = EscalationNotification(
            fault_id=report.fault_id,
            fault_type=report.fault_type,
            severity=report.severity,
            description=report.description,
            required_action=report.required_human_action,
            fault_report_path=f"{report.fault_id}.yaml",
            sla_hours=sla_hours,
        )
        
        # 实际实现中，这里会发送邮件/Slack 消息等
        # 现在只打印到控制台
        print("\n" + "=" * 60)
        print("ESCALATION NOTIFICATION")
        print("=" * 60)
        print(notification.to_message())
        print("=" * 60)
        
        # 更新报告
        report.status = "escalated"
        report.escalation_path = [
            {"role": r.get("role"), "notified_at": datetime.now().isoformat()}
            for r in recipients
        ]
        
        return {
            "fault_id": report.fault_id,
            "notified_recipients": recipients,
            "escalated_at": report.detected_at,
            "sla_deadline": sla_hours,
        }


# ========== 便捷函数 ==========

async def detect_faults(context: Dict[str, Any]) -> List[FaultReport]:
    """
    检测 Fault 并生成报告
    
    便捷函数
    """
    detector = FaultDetector()
    reporter = FaultReporter()
    
    faults = await detector.detect_all(context)
    reports = []
    
    for fault in faults:
        report = reporter.generate_report(fault, context)
        reporter.save_report(report)
        reports.append(report)
    
    return reports


async def escalate_fault(report: FaultReport) -> Dict[str, Any]:
    """
    上报 Fault
    
    便捷函数
    """
    manager = EscalationManager()
    return await manager.send_escalation(report)

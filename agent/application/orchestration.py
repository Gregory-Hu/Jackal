"""
应用层：Orchestration（编排协调）

职责：
- 管理智能体的生命周期（创建、销毁、状态监控）
- 负责任务的分解、分发与进度跟踪
- 协调多个智能体的工作流

使用 OpenHands SDK 作为底层执行引擎
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import asyncio
import yaml

# 内部消息总线（用于系统内部模块间通信）
from infra import (
    Message, MessageType, MessagePriority,
    get_message_bus, get_module_registry,
    ModuleType, ModuleStatus, ModuleInfo,
    MCPConfig, get_mcp_client_manager, initialize_mcp_tools,
    # Fault 检测与 Escalation
    FaultDetector, FaultReporter, EscalationManager,
    detect_faults, escalate_fault, FaultReport,
)

# 记忆服务
from memory import MemoryService, MemoryType, get_memory_service

# OpenHands SDK
from openhands.sdk import LLM, Agent, Conversation
from openhands.tools.preset.default import get_default_agent as get_default_tools
from openhands.sdk.tool import Tool


@dataclass
class TaskPlan:
    """
    任务计划

    任务分解后的执行计划
    """
    plan_id: str
    task_id: str
    task_name: str
    task_description: str

    # 子任务分解
    sub_tasks: List[Dict[str, Any]] = field(default_factory=list)

    # 执行状态
    status: str = "pending"  # pending, running, completed, failed
    current_step: int = 0

    # 结果
    results: List[Dict[str, Any]] = field(default_factory=list)

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status,
            "sub_tasks": self.sub_tasks,
            "current_step": self.current_step,
            "results": self.results,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class SOP:
    """
    标准操作程序（SOP）

    从 Markdown 文件加载
    """
    sop_id: str
    name: str
    description: str

    # 步骤定义
    steps: List[Dict[str, Any]] = field(default_factory=list)

    # 条件分支
    conditions: List[Dict[str, Any]] = field(default_factory=list)

    # 元数据
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_markdown(cls, markdown_path: str) -> "SOP":
        """从 Markdown 文件加载 SOP"""
        with open(markdown_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 解析 YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                yaml_content = parts[1]
                data = yaml.safe_load(yaml_content) or {}

                return cls(
                    sop_id=data.get("sop_id", str(uuid.uuid4())[:8]),
                    name=data.get("name", "Unnamed SOP"),
                    description=data.get("description", ""),
                    steps=data.get("steps", []),
                    conditions=data.get("conditions", []),
                    version=data.get("version", "1.0"),
                    tags=data.get("tags", []),
                )

        return cls(
            sop_id=str(uuid.uuid4())[:8],
            name="Unnamed SOP",
            description="No description",
        )


class OrchestrationService:
    """
    编排协调服务

    核心职责：
    1. 任务分解与规划
    2. 智能体调度（使用 OpenHands SDK Agent）
    3. 进度跟踪
    4. 异常处理
    """

    def __init__(
        self,
        orchestrator_id: Optional[str] = None,
        memory_service: Optional[MemoryService] = None,
        llm: Optional[LLM] = None,
    ):
        self.orchestrator_id = orchestrator_id or f"orchestrator_{uuid.uuid4().hex[:8]}"
        self.memory = memory_service or get_memory_service()
        
        # 使用内部消息总线替代原来的 MessageNetwork
        self.message_bus = get_message_bus()
        
        # LLM 实例
        self.llm = llm
        self._llm_initialized = False
        
        # 管理的智能体（使用 OpenHands SDK Agent）
        self.managed_agents: Dict[str, Dict[str, Any]] = {}
        
        # 任务计划
        self.task_plans: Dict[str, TaskPlan] = {}
        
        # 加载的 SOP
        self.sops: Dict[str, SOP] = {}
        
        # 运行状态
        self._running = False
        self._task_queue: asyncio.Queue = asyncio.Queue()
        
        # MCP 工具
        self._mcp_tools: List[Tool] = []
        
        # Fault 检测与 Escalation
        self.fault_detector = FaultDetector()
        self.fault_reporter = FaultReporter()
        self.escalation_manager = EscalationManager()
        self._active_faults: Dict[str, FaultReport] = {}  # task_id -> FaultReport

        # 注册到模块注册表
        self._register_self()

        # 注册消息处理器
        self._register_message_handlers()

    async def initialize_llm(self) -> None:
        """初始化 LLM（如果未提供）"""
        if self.llm is None and not self._llm_initialized:
            try:
                from config import get_config
                config = get_config()
                if config.is_llm_configured:
                    self.llm = LLM(
                        model=config.llm_model,
                        api_key=config.llm_api_key,
                        base_url=config.llm_base_url,
                    )
                    self._llm_initialized = True
            except Exception as e:
                print(f"Failed to initialize LLM: {e}")

    async def initialize_mcp_tools(self, config: Optional[MCPConfig] = None) -> List[Tool]:
        """初始化 MCP 工具"""
        self._mcp_tools = await initialize_mcp_tools(config)
        return self._mcp_tools

    def _register_self(self) -> None:
        """注册自己到模块注册表"""
        registry = get_module_registry()

        module_info = ModuleInfo(
            module_id=self.orchestrator_id,
            module_type=ModuleType.ORCHESTRATION,
            name="Orchestration Service",
            description="Task orchestration and agent coordination",
            status=ModuleStatus.READY,
            capabilities=["task_decomposition", "agent_scheduling", "progress_tracking"],
        )

        registry.register(module_info)

    def _register_message_handlers(self) -> None:
        """注册消息处理器"""
        self.message_bus.register_handler(
            MessageType.START_TASK,
            self._handle_start_task,
        )

        self.message_bus.register_handler(
            MessageType.STOP_TASK,
            self._handle_stop_task,
        )

        self.message_bus.register_handler(
            MessageType.EVENT_TASK_COMPLETED,
            self._handle_task_completed,
        )

    # ========== 智能体管理 ==========

    async def create_agent(
        self,
        agent_type: str = "default",
        agent_id: Optional[str] = None,
        workspace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建并注册执行智能体
        
        使用 OpenHands SDK 的 Agent
        """
        # 确保 LLM 已初始化
        if not self.llm:
            await self.initialize_llm()
        
        if not self.llm:
            raise RuntimeError("LLM not configured. Call initialize_llm() first or configure .env")
        
        agent_id = agent_id or f"{agent_type}_{uuid.uuid4().hex[:8]}"
        
        # 使用 OpenHands 的默认 Agent
        if agent_type == "default":
            agent = get_default_tools(llm=self.llm, cli_mode=True)
        else:
            # 自定义 Agent
            agent = Agent(
                llm=self.llm,
                tools=[],  # 可以添加自定义工具
            )
        
        # 创建对话
        workspace = workspace or "./workspace"
        conversation = Conversation(
            agent=agent,
            workspace=workspace,
        )
        
        # 存储 Agent 信息
        agent_info = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "agent": agent,
            "conversation": conversation,
            "workspace": workspace,
            "status": "ready",
            "created_at": datetime.now().isoformat(),
        }
        
        self.managed_agents[agent_id] = agent_info
        
        # 发布事件
        event = Message(
            message_type=MessageType.EVENT_TASK_STARTED,
            source=self.orchestrator_id,
            topic="agent_events",
            payload={"agent_id": agent_id, "event": "agent_created"},
        )
        await self.message_bus.publish(event)
        
        return agent_info

    def destroy_agent(self, agent_id: str) -> bool:
        """销毁执行智能体"""
        agent_info = self.managed_agents.pop(agent_id, None)
        if agent_info:
            # 清理对话等资源
            agent_info["conversation"] = None
            return True
        return False

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取智能体信息"""
        return self.managed_agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有管理的智能体"""
        return [
            {
                "agent_id": info["agent_id"],
                "agent_type": info["agent_type"],
                "status": info["status"],
                "workspace": info["workspace"],
            }
            for info in self.managed_agents.values()
        ]

    # ========== SOP 管理 ==========

    def load_sop(self, sop_path: str) -> SOP:
        """加载 SOP 文件"""
        sop = SOP.from_markdown(sop_path)
        self.sops[sop.sop_id] = sop
        return sop

    def get_sop(self, sop_id: str) -> Optional[SOP]:
        """获取 SOP"""
        return self.sops.get(sop_id)

    # ========== Fault 检测与 Escalation ==========

    async def pre_flight_check(self, context: Dict[str, Any]) -> List[FaultReport]:
        """
        任务执行前的预检检查
        
        检测所有可能的 Fault 并上报
        """
        faults = await self.fault_detector.detect_all(context)
        
        if faults:
            print(f"\n⚠️ 检测到 {len(faults)} 个 Fault，正在生成报告...")
            
            reports = []
            for fault in faults:
                # 生成报告
                report = self.fault_reporter.generate_report(fault, context)
                self.fault_reporter.save_report(report)
                
                # 发送 Escalation
                escalation_result = await escalate_fault(report)
                
                # 记录活跃 Fault
                self._active_faults[context.get("task_id", report.fault_id)] = report
                
                reports.append(report)
                print(f"  📄 Fault 报告已保存：{report.fault_id}.yaml")
            
            return reports
        
        return []

    async def handle_fault(self, fault_report: FaultReport) -> bool:
        """
        处理 Fault
        
        Returns:
            bool: 是否已解决
        """
        # 检查 Fault 状态
        if fault_report.status == "resolved":
            # 验证修复
            context = {
                "workspace": fault_report.diagnostics.get("workspace", ""),
                "task_id": fault_report.task_id,
            }
            
            # 重新检测该 Fault 类型
            recheck_faults = await self.fault_detector.detect_all(context)
            recheck_fault_types = [f.fault_type.value for f in recheck_faults]
            
            if fault_report.fault_type.value not in recheck_fault_types:
                # Fault 已修复
                fault_report.status = "closed"
                self.fault_reporter.update_report(fault_report)
                
                # 从活跃 Fault 中移除
                if fault_report.task_id in self._active_faults:
                    del self._active_faults[fault_report.task_id]
                
                print(f"✅ Fault {fault_report.fault_id} 已解决并关闭")
                return True
            else:
                print(f"⚠️ Fault {fault_report.fault_id} 验证失败，问题仍然存在")
                fault_report.status = "verification_failed"
                self.fault_reporter.update_report(fault_report)
                return False
        
        return False

    async def wait_for_human_review(self, task_id: str, timeout_hours: int = 24) -> bool:
        """
        等待 Human Review
        
        Returns:
            bool: 是否收到 Review
        """
        print(f"\n⏳ 等待 Human Review...(超时：{timeout_hours}小时)")
        
        # 实际实现中，这里会轮询 Fault 报告状态
        # 或者通过 WebSocket 等接收通知
        # 现在简化为检查文件状态
        
        import time
        start_time = time.time()
        timeout_seconds = timeout_hours * 3600
        
        while time.time() - start_time < timeout_seconds:
            # 检查 Fault 报告是否已解决
            if task_id in self._active_faults:
                report = self._active_faults[task_id]
                loaded_report = self.fault_reporter.load_report(report.fault_id)
                
                if loaded_report and loaded_report.status == "resolved":
                    print(f"✅ 收到 Human Review: {loaded_report.resolution_description}")
                    return True
            
            # 等待一段时间后重试
            await asyncio.sleep(5)  # 每 5 秒检查一次
        
        print(f"⏰ Human Review 超时 ({timeout_hours}小时)")
        return False

    async def resolve_fault(
        self,
        fault_id: str,
        resolution_description: str,
        human_id: str = "human_reviewer",
        continue_task: bool = True,
        notes: Optional[str] = None,
    ) -> bool:
        """
        解决 Fault（由 Human 调用）
        
        Args:
            fault_id: Fault ID
            resolution_description: 解决描述
            human_id: Human  reviewer ID
            continue_task: 是否继续执行任务
            notes: 额外说明
            
        Returns:
            bool: 是否成功解决
        """
        # 加载 Fault 报告
        report = self.fault_reporter.load_report(fault_id)
        if not report:
            print(f"❌ Fault 报告不存在：{fault_id}")
            return False
        
        # 更新报告
        report.status = "resolved"
        report.resolved_at = datetime.now().isoformat()
        report.resolved_by = human_id
        report.resolution_description = resolution_description
        report.human_notes = notes
        
        self.fault_reporter.update_report(report)
        
        print(f"✅ Fault {fault_id} 已标记为已解决")
        if notes:
            print(f"   说明：{notes}")
        
        return True

    # ========== 任务编排 ==========

    async def submit_task(self, task: Dict[str, Any]) -> str:
        """
        提交任务

        返回任务 ID
        """
        task_id = task.get("task_id", str(uuid.uuid4())[:8])

        # 创建任务计划
        plan = await self._decompose_task(task)
        self.task_plans[task_id] = plan

        # 放入任务队列
        await self._task_queue.put(plan)

        # 存储到记忆
        if self.memory:
            self.memory.store_task_state(
                task_id=task_id,
                state=plan.to_dict(),
                created_by=self.orchestrator_id,
            )

        return task_id

    async def _decompose_task(self, task: Dict[str, Any]) -> TaskPlan:
        """
        任务分解

        将高层任务分解为可执行的子任务
        """
        task_id = task.get("task_id", str(uuid.uuid4())[:8])

        plan = TaskPlan(
            plan_id=str(uuid.uuid4())[:8],
            task_id=task_id,
            task_name=task.get("name", "Unnamed Task"),
            task_description=task.get("description", ""),
        )

        # 检查是否指定了 SOP
        sop_id = task.get("sop_id")
        if sop_id and sop_id in self.sops:
            sop = self.sops[sop_id]
            plan.sub_tasks = sop.steps
        else:
            # 默认分解：单步骤任务
            plan.sub_tasks = [
                {
                    "step_id": "step_1",
                    "name": task.get("name", "Task"),
                    "action": task.get("action", "execute"),
                    "params": task.get("params", {}),
                    "agent_type": task.get("agent_type", "default"),
                }
            ]

        return plan

    async def execute_plan(self, plan: TaskPlan) -> Dict[str, Any]:
        """
        执行任务计划

        使用 OpenHands SDK Agent 按步骤执行子任务
        
        在执行前会进行 Fault 预检检查
        """
        # ========== Fault 预检检查 ==========
        context = {
            "task_id": plan.task_id,
            "workspace": "./workspace",  # 或者从配置获取
            "agent_id": self.orchestrator_id,
            "jd_id": "",  # 可选
            "current_step": "pre_flight_check",
        }
        
        faults = await self.pre_flight_check(context)
        
        if faults:
            # 有 Fault，等待 Human Review
            print(f"\n⏸️  任务 {plan.task_id} 暂停，等待 Fault 解决...")
            
            # 等待 Human Review
            review_received = await self.wait_for_human_review(plan.task_id)
            
            if not review_received:
                plan.status = "paused"
                plan.completed_at = datetime.now()
                return {
                    "status": "paused",
                    "reason": "waiting_for_human_review",
                    "faults": [f.fault_id for f in faults],
                }
            
            # 验证 Fault 已解决
            for report in faults:
                resolved = await self.handle_fault(report)
                if not resolved:
                    plan.status = "failed"
                    plan.completed_at = datetime.now()
                    return {
                        "status": "failed",
                        "reason": "fault_verification_failed",
                        "fault_id": report.fault_id,
                    }
            
            print(f"✅ 所有 Fault 已解决，继续执行任务 {plan.task_id}")
        
        # ========== 执行任务 ==========
        plan.status = "running"
        plan.started_at = datetime.now()

        results = []

        for i, sub_task in enumerate(plan.sub_tasks):
            plan.current_step = i

            # 获取或创建智能体
            agent_type = sub_task.get("agent_type", "default")
            agent_info = self._get_or_create_agent(agent_type)

            if not agent_info:
                results.append({
                    "step_id": sub_task.get("step_id"),
                    "status": "failed",
                    "error": f"Failed to create agent for type: {agent_type}",
                })
                continue

            # 使用 OpenHands Conversation 执行任务
            try:
                conversation = agent_info["conversation"]
                task_description = sub_task.get("name", "")
                if sub_task.get("params"):
                    task_description += f"\n\nParameters: {sub_task['params']}"

                conversation.send_message(task_description)
                conversation.run()

                # 获取结果
                result = conversation.state.events[-1]
                if hasattr(result, "llm_message"):
                    from openhands.sdk.llm import content_to_str
                    result_content = "".join(content_to_str(result.llm_message.content))
                else:
                    result_content = str(result)

                results.append({
                    "step_id": sub_task.get("step_id"),
                    "status": "success",
                    "data": result_content,
                })

            except Exception as e:
                results.append({
                    "step_id": sub_task.get("step_id"),
                    "status": "failed",
                    "error": str(e),
                })

        plan.results = results
        plan.completed_at = datetime.now()

        # 判断整体状态
        failed_count = sum(1 for r in results if r.get("status") == "failed")
        plan.status = "failed" if failed_count > 0 else "completed"

        # 更新记忆
        if self.memory:
            self.memory.store_task_state(
                task_id=plan.task_id,
                state=plan.to_dict(),
                created_by=self.orchestrator_id,
            )

        # 发布完成事件
        event = Message(
            message_type=MessageType.EVENT_TASK_COMPLETED,
            source=self.orchestrator_id,
            topic="task_events",
            payload={"status": plan.status, "results": results},
        )
        await self.message_bus.publish(event)

        return plan.to_dict()

    def _get_or_create_agent(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """获取或创建智能体"""
        # 查找现有智能体
        for agent_id, info in self.managed_agents.items():
            if info["agent_type"] == agent_type and info["status"] == "ready":
                return info

        # 创建新智能体
        try:
            return asyncio.run_coroutine_threadsafe(
                self.create_agent(agent_type),
                asyncio.get_event_loop()
            ).result(timeout=30.0)
        except Exception:
            return None

    # ========== 消息处理 ==========

    async def _handle_start_task(self, message: Message) -> None:
        """处理启动任务消息"""
        task = message.payload.get("task", {})
        task_id = await self.submit_task(task)

        # 响应
        response = Message(
            message_type=MessageType.STATUS_RESPONSE,
            source=self.orchestrator_id,
            target=message.source,
            payload={"task_id": task_id, "status": "submitted"},
            correlation_id=message.message_id,
        )
        await self.message_bus.respond(message, response)

    async def _handle_stop_task(self, message: Message) -> None:
        """处理停止任务消息"""
        task_id = message.payload.get("task_id")

        if task_id and task_id in self.task_plans:
            plan = self.task_plans[task_id]
            plan.status = "cancelled"
            plan.completed_at = datetime.now()

        response = Message(
            message_type=MessageType.STATUS_RESPONSE,
            source=self.orchestrator_id,
            target=message.source,
            payload={"task_id": task_id, "status": "stopped"},
            correlation_id=message.message_id,
        )
        await self.message_bus.respond(message, response)

    async def _handle_task_completed(self, message: Message) -> None:
        """处理任务完成事件"""
        # 可以用于触发后续任务或报告生成
        pass

    # ========== 运行循环 ==========

    async def start(self) -> None:
        """启动编排服务"""
        self._running = True

        while self._running:
            try:
                # 获取任务计划
                try:
                    plan = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # 执行计划
                await self.execute_plan(plan)

            except Exception as e:
                print(f"Orchestration error: {e}")

    def stop(self) -> None:
        """停止编排服务"""
        self._running = False

    # ========== 状态查询 ==========

    def get_status(self) -> Dict[str, Any]:
        """获取编排服务状态"""
        return {
            "orchestrator_id": self.orchestrator_id,
            "managed_agents": len(self.managed_agents),
            "active_plans": len([p for p in self.task_plans.values() if p.status == "running"]),
            "completed_plans": len([p for p in self.task_plans.values() if p.status == "completed"]),
            "sops_loaded": len(self.sops),
            "mcp_tools": len(self._mcp_tools),
            "llm_initialized": self._llm_initialized,
        }

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        plan = self.task_plans.get(task_id)
        if plan:
            return plan.to_dict()

        # 从记忆中获取
        if self.memory:
            return self.memory.get_task_state(task_id)
        
        return None

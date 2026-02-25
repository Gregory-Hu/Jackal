"""
基础设施层：内部消息总线（Internal Message Bus）

⚠️ 注意：这是系统内部消息总线，不是 Anthropic 的 Model Context Protocol (MCP)
   
如需与外部 MCP Servers 交互，请使用 openhands.mcp 模块

作为整个系统的"总线"，提供可靠、异步的消息传递机制。
所有模块通过该网络进行通信，实现完全解耦。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from datetime import datetime
import uuid
import asyncio
import json


class MessageType(Enum):
    """消息类型（内部协议）"""
    # 系统级消息
    CREATE_AGENT = "system.create_agent"
    DESTROY_AGENT = "system.destroy_agent"
    START_TASK = "system.start_task"
    STOP_TASK = "system.stop_task"
    STATUS_QUERY = "system.status_query"
    STATUS_RESPONSE = "system.status_response"
    SYNC_STATE = "system.sync_state"

    # 智能体间协作
    TASK_REQUEST = "agent.task_request"
    TASK_RESPONSE = "agent.task_response"
    COLLABORATION_REQUEST = "agent.collaboration_request"
    COLLABORATION_RESPONSE = "agent.collaboration_response"
    NEGOTIATION = "agent.negotiation"
    CONSENSUS = "agent.consensus"

    # 事件通知
    EVENT_TASK_STARTED = "event.task_started"
    EVENT_TASK_COMPLETED = "event.task_completed"
    EVENT_TASK_FAILED = "event.task_failed"
    EVENT_MEMORY_UPDATED = "event.memory_updated"
    EVENT_REPORT_GENERATED = "event.report_generated"


class MessagePriority(Enum):
    """消息优先级"""
    CRITICAL = 0  # 关键消息（错误、停止）
    HIGH = 1      # 高优先级（任务分配）
    NORMAL = 2    # 普通消息
    LOW = 3       # 低优先级（日志、状态同步）


@dataclass
class Message:
    """
    消息结构

    所有模块间通信都通过此消息结构
    """
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    message_type: MessageType = MessageType.STATUS_QUERY
    priority: MessagePriority = MessagePriority.NORMAL

    source: str = ""           # 发送方 ID
    target: str = ""           # 接收方 ID（广播时为空）
    topic: str = ""            # 主题（用于发布/订阅）

    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None  # 关联消息 ID（用于请求/响应）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "source": self.source,
            "target": self.target,
            "topic": self.topic,
            "payload": self.payload,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())[:12]),
            message_type=MessageType(data.get("message_type", "system.status_query")),
            priority=MessagePriority(data.get("priority", 2)),
            source=data.get("source", ""),
            target=data.get("target", ""),
            topic=data.get("topic", ""),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            correlation_id=data.get("correlation_id"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        return cls.from_dict(json.loads(json_str))

    # ========== 便捷构造方法 ==========

    @classmethod
    def create_agent(cls, agent_id: str, agent_type: str, config: Dict[str, Any]) -> "Message":
        return cls(
            message_type=MessageType.CREATE_AGENT,
            priority=MessagePriority.HIGH,
            source="orchestrator",
            payload={"agent_id": agent_id, "agent_type": agent_type, "config": config},
        )

    @classmethod
    def task_request(cls, source: str, target: str, task: Dict[str, Any]) -> "Message":
        return cls(
            message_type=MessageType.TASK_REQUEST,
            source=source,
            target=target,
            payload={"task": task},
        )

    @classmethod
    def task_response(cls, source: str, target: str, result: Dict[str, Any], correlation_id: str) -> "Message":
        return cls(
            message_type=MessageType.TASK_RESPONSE,
            source=source,
            target=target,
            payload={"result": result},
            correlation_id=correlation_id,
        )

    @classmethod
    def collaboration_request(cls, source: str, topic: str, context: Dict[str, Any]) -> "Message":
        return cls(
            message_type=MessageType.COLLABORATION_REQUEST,
            source=source,
            topic=topic,
            payload={"context": context},
        )

    @classmethod
    def event_task_completed(cls, source: str, task_id: str, result: Dict[str, Any]) -> "Message":
        return cls(
            message_type=MessageType.EVENT_TASK_COMPLETED,
            source=source,
            topic="task_events",
            payload={"task_id": task_id, "result": result},
        )


@dataclass
class Subscription:
    """订阅配置"""
    subscriber_id: str
    topic: str
    callback: Callable[["Message"], Awaitable[None]]
    filter_fn: Optional[Callable[["Message"], bool]] = None


class MessageBus:
    """
    内部消息总线：系统通信总线

    ⚠️ 注意：这是内部消息总线，不是 Anthropic MCP
    
    支持：
    - 发布/订阅模式
    - 点对点消息
    - 请求/响应模式
    - 优先级队列
    - 异步处理
    """

    def __init__(self):
        self._subscriptions: Dict[str, List[Subscription]] = {}  # topic -> subscriptions
        self._handlers: Dict[MessageType, Callable[["Message"], Awaitable[Any]]] = {}
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._message_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._message_counter = 0

    # ========== 订阅管理 ==========

    def subscribe(
        self,
        subscriber_id: str,
        topic: str,
        callback: Callable[["Message"], Awaitable[None]],
        filter_fn: Optional[Callable[["Message"], bool]] = None,
    ) -> None:
        """订阅主题"""
        subscription = Subscription(
            subscriber_id=subscriber_id,
            topic=topic,
            callback=callback,
            filter_fn=filter_fn,
        )

        if topic not in self._subscriptions:
            self._subscriptions[topic] = []
        self._subscriptions[topic].append(subscription)

    def unsubscribe(self, subscriber_id: str, topic: str) -> None:
        """取消订阅"""
        if topic in self._subscriptions:
            self._subscriptions[topic] = [
                s for s in self._subscriptions[topic]
                if s.subscriber_id != subscriber_id
            ]

    # ========== 消息处理注册 ==========

    def register_handler(
        self,
        message_type: MessageType,
        handler: Callable[["Message"], Awaitable[Any]],
    ) -> None:
        """注册消息处理器"""
        self._handlers[message_type] = handler

    # ========== 消息发送 ==========

    async def publish(self, message: Message) -> None:
        """发布消息到主题"""
        topic = message.topic
        if topic not in self._subscriptions:
            return

        for subscription in self._subscriptions[topic]:
            # 应用过滤器
            if subscription.filter_fn and not subscription.filter_fn(message):
                continue

            # 异步回调
            asyncio.create_task(subscription.callback(message))

    async def send(self, message: Message) -> None:
        """发送消息（放入队列）"""
        priority = message.priority.value
        await self._message_queue.put((priority, message))

    async def send_and_wait(
        self,
        message: Message,
        timeout: float = 30.0,
    ) -> Optional[Message]:
        """发送消息并等待响应"""
        # 创建 correlation ID
        message.correlation_id = message.message_id

        # 创建 Future 等待响应
        future = asyncio.Future()
        self._pending_responses[message.correlation_id] = future

        # 发送请求
        await self.send(message)

        try:
            # 等待响应
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self._pending_responses.pop(message.correlation_id, None)

    async def respond(self, request: Message, response: Message) -> None:
        """发送响应"""
        response.correlation_id = request.message_id
        await self.publish(response)

        # 唤醒等待的 Future
        if request.message_id in self._pending_responses:
            self._pending_responses[request.message_id].set_result(response)

    # ========== 消息处理循环 ==========

    async def start(self) -> None:
        """启动消息处理循环"""
        self._running = True

        while self._running:
            try:
                # 获取消息（带超时）
                try:
                    priority, message = await asyncio.wait_for(
                        self._message_queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                # 处理消息
                await self._process_message(message)

            except Exception as e:
                # 记录错误，继续处理
                print(f"Message processing error: {e}")

    def stop(self) -> None:
        """停止消息处理循环"""
        self._running = False

    async def _process_message(self, message: Message) -> None:
        """处理单条消息"""
        # 1. 检查是否是响应消息
        if message.correlation_id:
            if message.message_type == MessageType.TASK_RESPONSE:
                if message.correlation_id in self._pending_responses:
                    self._pending_responses[message.correlation_id].set_result(message)
                    return

        # 2. 发布到主题
        if message.topic:
            await self.publish(message)

        # 3. 调用注册的处理器
        if message.message_type in self._handlers:
            handler = self._handlers[message.message_type]
            try:
                await handler(message)
            except Exception as e:
                print(f"Handler error for {message.message_type}: {e}")

    # ========== 状态查询 ==========

    def get_stats(self) -> Dict[str, Any]:
        """获取总线统计"""
        return {
            "queue_size": self._message_queue.qsize(),
            "subscription_count": sum(len(subs) for subs in self._subscriptions.values()),
            "topics": list(self._subscriptions.keys()),
            "handlers": list(self._handlers.keys()),
            "pending_responses": len(self._pending_responses),
        }


# ========== 全局消息总线实例 ==========

_default_bus: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """获取全局消息总线实例"""
    global _default_bus
    if _default_bus is None:
        _default_bus = MessageBus()
    return _default_bus


def set_message_bus(bus: MessageBus) -> None:
    """设置全局消息总线实例"""
    global _default_bus
    _default_bus = bus

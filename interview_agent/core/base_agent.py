"""
通用Agent基类 - 参考Dify和n8n的架构设计
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from datetime import datetime
import logging
from pathlib import Path
import uuid


class AgentStatus(Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class MessageType(Enum):
    """消息类型枚举"""
    SYSTEM = "system"
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"
    ERROR = "error"


@dataclass
class AgentMessage:
    """Agent消息结构"""
    type: MessageType
    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    sender: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "sender": self.sender
        }


@dataclass
class AgentContext:
    """Agent执行上下文"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    variables: Dict[str, Any] = field(default_factory=dict)
    messages: List[AgentMessage] = field(default_factory=list)
    files: Dict[str, Path] = field(default_factory=dict)
    status: AgentStatus = AgentStatus.IDLE
    error: Optional[str] = None
    
    def add_message(self, message: AgentMessage):
        """添加消息到上下文"""
        self.messages.append(message)
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(key, default)
    
    def set_variable(self, key: str, value: Any):
        """设置变量"""
        self.variables[key] = value
    
    def add_file(self, name: str, path: Path):
        """添加文件引用"""
        self.files[name] = path
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "variables": self.variables,
            "messages": [msg.to_dict() for msg in self.messages],
            "files": {k: str(v) for k, v in self.files.items()},
            "status": self.status.value,
            "error": self.error
        }


class BaseAgent(ABC):
    """通用Agent基类"""
    
    def __init__(self, 
                 name: str,
                 description: str = "",
                 config: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.config = config or {}
        self.logger = logging.getLogger(f"Agent.{name}")
        self._hooks: Dict[str, List[Callable]] = {
            "before_run": [],
            "after_run": [],
            "on_error": [],
            "on_message": []
        }
        self._tools: Dict[str, Callable] = {}
        
    def register_hook(self, event: str, callback: Callable):
        """注册钩子函数"""
        if event in self._hooks:
            self._hooks[event].append(callback)
    
    def register_tool(self, name: str, func: Callable):
        """注册工具函数"""
        self._tools[name] = func
    
    async def _trigger_hooks(self, event: str, *args, **kwargs):
        """触发钩子函数"""
        for hook in self._hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(*args, **kwargs)
                else:
                    hook(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Hook {event} error: {e}")
    
    @abstractmethod
    async def process(self, context: AgentContext) -> AgentContext:
        """处理逻辑 - 子类必须实现"""
        pass
    
    async def run(self, context: Optional[AgentContext] = None) -> AgentContext:
        """运行Agent"""
        if context is None:
            context = AgentContext()
        
        context.status = AgentStatus.RUNNING
        
        try:
            # 触发开始前的钩子
            await self._trigger_hooks("before_run", context)
            
            # 执行处理逻辑
            context = await self.process(context)
            
            context.status = AgentStatus.COMPLETED
            
            # 触发完成后的钩子
            await self._trigger_hooks("after_run", context)
            
        except Exception as e:
            context.status = AgentStatus.FAILED
            context.error = str(e)
            self.logger.error(f"Agent {self.name} failed: {e}")
            
            # 触发错误钩子
            await self._trigger_hooks("on_error", e, context)
            
        return context
    
    def add_message(self, context: AgentContext, content: Any, 
                   msg_type: MessageType = MessageType.AGENT,
                   metadata: Dict[str, Any] = None):
        """向上下文添加消息"""
        message = AgentMessage(
            type=msg_type,
            content=content,
            sender=self.name,
            metadata=metadata or {}
        )
        context.add_message(message)
        
        # 触发消息钩子
        asyncio.create_task(self._trigger_hooks("on_message", message, context))
    
    async def call_tool(self, tool_name: str, *args, **kwargs) -> Any:
        """调用工具函数"""
        if tool_name not in self._tools:
            raise ValueError(f"Tool {tool_name} not found")
        
        tool = self._tools[tool_name]
        if asyncio.iscoroutinefunction(tool):
            return await tool(*args, **kwargs)
        else:
            return tool(*args, **kwargs)


class ChainAgent(BaseAgent):
    """链式Agent - 按顺序执行多个子Agent"""
    
    def __init__(self, name: str, agents: List[BaseAgent], **kwargs):
        super().__init__(name, **kwargs)
        self.agents = agents
    
    async def process(self, context: AgentContext) -> AgentContext:
        """按顺序执行所有子Agent"""
        for agent in self.agents:
            self.logger.info(f"Running agent: {agent.name}")
            context = await agent.run(context)
            
            if context.status == AgentStatus.FAILED:
                break
        
        return context


class ConditionalAgent(BaseAgent):
    """条件Agent - 根据条件选择执行路径"""
    
    def __init__(self, name: str, 
                 condition: Callable[[AgentContext], bool],
                 true_agent: BaseAgent,
                 false_agent: Optional[BaseAgent] = None,
                 **kwargs):
        super().__init__(name, **kwargs)
        self.condition = condition
        self.true_agent = true_agent
        self.false_agent = false_agent
    
    async def process(self, context: AgentContext) -> AgentContext:
        """根据条件执行相应的Agent"""
        if await self._evaluate_condition(context):
            return await self.true_agent.run(context)
        elif self.false_agent:
            return await self.false_agent.run(context)
        return context
    
    async def _evaluate_condition(self, context: AgentContext) -> bool:
        """评估条件"""
        if asyncio.iscoroutinefunction(self.condition):
            return await self.condition(context)
        else:
            return self.condition(context)


class LoopAgent(BaseAgent):
    """循环Agent - 重复执行直到满足条件"""
    
    def __init__(self, name: str,
                 agent: BaseAgent,
                 continue_condition: Callable[[AgentContext], bool],
                 max_iterations: int = 10,
                 **kwargs):
        super().__init__(name, **kwargs)
        self.agent = agent
        self.continue_condition = continue_condition
        self.max_iterations = max_iterations
    
    async def process(self, context: AgentContext) -> AgentContext:
        """循环执行Agent直到条件不满足或达到最大次数"""
        iteration = 0
        
        while iteration < self.max_iterations:
            if not await self._should_continue(context):
                break
            
            context = await self.agent.run(context)
            iteration += 1
            
            if context.status == AgentStatus.FAILED:
                break
        
        return context
    
    async def _should_continue(self, context: AgentContext) -> bool:
        """判断是否继续循环"""
        if asyncio.iscoroutinefunction(self.continue_condition):
            return await self.continue_condition(context)
        else:
            return self.continue_condition(context) 
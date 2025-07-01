"""
智能对话管理器 - 管理实时语音面试对话流程
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from .llm_client import WildcardLLMClient, Message
from .interview_conductor import InterviewConductor, InterviewSession, MessageRole


class DialogState(Enum):
    """对话状态"""
    INITIALIZING = "initializing"
    GREETING = "greeting"
    QUESTIONING = "questioning"
    LISTENING = "listening" 
    FOLLOWING_UP = "following_up"
    SUPERVISOR_INTERVENTION = "supervisor_intervention"
    TRANSITIONING = "transitioning"
    CLOSING = "closing"
    COMPLETED = "completed"


@dataclass
class DialogContext:
    """对话上下文"""
    current_state: DialogState = DialogState.INITIALIZING
    current_question_index: int = 0
    current_section_index: int = 0
    follow_up_count: int = 0
    max_follow_ups: int = 2
    conversation_history: List[Dict] = field(default_factory=list)
    supervisor_instructions: List[str] = field(default_factory=list)
    pending_transitions: List[str] = field(default_factory=list)
    
    def add_conversation(self, role: str, content: str, metadata: Dict = None):
        """添加对话记录"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })


class IntelligentDialogManager:
    """智能对话管理器"""
    
    def __init__(self, 
                 llm_client: WildcardLLMClient,
                 interview_plan: Dict,
                 candidate_name: str = "候选人"):
        self.llm_client = llm_client
        self.interview_plan = interview_plan
        self.candidate_name = candidate_name
        self.context = DialogContext()
        self.logger = logging.getLogger(__name__)
        
        # 回调函数
        self.on_state_change: Optional[Callable] = None
        self.on_audio_output: Optional[Callable] = None
        self.on_evaluation_update: Optional[Callable] = None
        
        # 面试会话管理
        self.conductor = InterviewConductor(llm_client)
        self.session: Optional[InterviewSession] = None
        
        # 确保持久化面试计划
        self.interview_plan = interview_plan
        
    def set_callbacks(self, 
                     on_state_change: Callable = None,
                     on_audio_output: Callable = None,
                     on_evaluation_update: Callable = None):
        """设置回调函数"""
        if on_state_change:
            self.on_state_change = on_state_change
        if on_audio_output:
            self.on_audio_output = on_audio_output
        if on_evaluation_update:
            self.on_evaluation_update = on_evaluation_update
    
    async def initialize_session(self) -> str:
        """初始化面试会话"""
        try:
            self.logger.info("初始化智能对话会话")
            
            # 设置初始状态
            self._update_state(DialogState.GREETING)
            
            # 生成开场白
            greeting = await self._generate_greeting()
            self.context.add_conversation("interviewer", greeting)
            
            return greeting
            
        except Exception as e:
            self.logger.error(f"初始化会话失败: {e}")
            raise
    
    async def process_candidate_input(self, text_input: str) -> str:
        """处理候选人输入"""
        try:
            self.logger.info(f"处理候选人输入: {text_input[:50]}...")
            
            # 记录候选人输入
            self.context.add_conversation("candidate", text_input)
            
            # 检查是否有监督员指令需要处理
            if self.context.supervisor_instructions:
                return await self._handle_supervisor_intervention(text_input)
            
            # 根据当前状态处理输入
            if self.context.current_state == DialogState.GREETING:
                return await self._handle_greeting_response(text_input)
            elif self.context.current_state == DialogState.LISTENING:
                return await self._handle_question_response(text_input)
            elif self.context.current_state == DialogState.FOLLOWING_UP:
                return await self._handle_followup_response(text_input)
            else:
                return await self._handle_general_response(text_input)
                
        except Exception as e:
            self.logger.error(f"处理输入失败: {e}")
            return "抱歉，我没有理解您的回答，能否再说一遍？"
    
    async def add_supervisor_instruction(self, instruction: str):
        """添加监督员指令"""
        self.logger.info(f"收到监督员指令: {instruction}")
        self.context.supervisor_instructions.append({
            "instruction": instruction,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_supervisor_intervention(self, candidate_input: str) -> str:
        """处理监督员干预"""
        self._update_state(DialogState.SUPERVISOR_INTERVENTION)
        
        # 获取最新的监督员指令
        latest_instruction = self.context.supervisor_instructions[-1]
        instruction_text = latest_instruction["instruction"]
        
        # 使用LLM分析指令并调整对话
        analysis_prompt = f"""
作为面试官，你收到了监督员的指令："{instruction_text}"

当前对话情况：
候选人刚才说："{candidate_input}"
当前面试进度：第{self.context.current_section_index + 1}个环节，第{self.context.current_question_index + 1}个问题

请根据监督员指令，生成合适的回应。你需要：
1. 自然地转换话题或调整提问方向
2. 不要让候选人感觉到突兀
3. 体现监督员的要求

请直接返回你作为面试官的回应内容。
"""
        
        messages = [
            Message(role="system", content="你是一位专业的面试官，能够灵活应对各种面试情况。"),
            Message(role="user", content=analysis_prompt)
        ]
        
        response = self.llm_client.chat_completion(messages)
        intervention_response = response.content
        
        # 记录干预
        self.context.add_conversation("interviewer", intervention_response, {
            "type": "supervisor_intervention",
            "instruction": instruction_text
        })
        
        # 清除已处理的指令
        self.context.supervisor_instructions.clear()
        
        # 根据指令类型调整状态
        if "下一个问题" in instruction_text or "跳过" in instruction_text:
            await self._move_to_next_question()
        elif "深入" in instruction_text or "追问" in instruction_text:
            self._update_state(DialogState.FOLLOWING_UP)
        else:
            self._update_state(DialogState.LISTENING)
        
        return intervention_response
    
    async def _handle_greeting_response(self, text_input: str) -> str:
        """处理开场回应"""
        # 简单确认后进入第一个问题
        self._update_state(DialogState.QUESTIONING)
        return await self._ask_current_question()
    
    async def _handle_question_response(self, text_input: str) -> str:
        """处理问题回答"""
        # 使用LLM分析回答质量
        current_question = self._get_current_question()
        if not current_question:
            return await self._close_interview()
        
        analysis = await self._analyze_response(text_input, current_question)
        
        # 根据分析结果决定下一步
        if analysis.get("needs_clarification"):
            return await self._ask_for_clarification(text_input, current_question)
        elif analysis.get("needs_follow_up") and self.context.follow_up_count < self.context.max_follow_ups:
            return await self._generate_follow_up(text_input, current_question)
        else:
            return await self._move_to_next_question()
    
    async def _handle_followup_response(self, text_input: str) -> str:
        """处理追问回答"""
        self.context.follow_up_count += 1
        
        # 给予反馈并决定是否继续追问
        if self.context.follow_up_count >= self.context.max_follow_ups:
            return await self._move_to_next_question()
        else:
            current_question = self._get_current_question()
            analysis = await self._analyze_response(text_input, current_question)
            
            if analysis.get("needs_follow_up"):
                return await self._generate_follow_up(text_input, current_question)
            else:
                return await self._move_to_next_question()
    
    async def _handle_general_response(self, text_input: str) -> str:
        """处理一般回应"""
        return "谢谢您的回答，让我们继续。"
    
    async def _generate_greeting(self) -> str:
        """生成开场白及第一个问题，将面试计划作为核心指令"""
        self.logger.info("基于面试计划生成开场白和第一个问题...")
        
        # 将面试计划转换为格式化的字符串，作为核心指令
        plan_str = json.dumps(self.interview_plan, ensure_ascii=False, indent=2)

        system_prompt = f"""
你是一名专业的AI面试官。你的任务是严格按照以下的JSON格式面试计划来主持一场技术面试。

你的职责：
1. **开场**: 首先，你需要根据计划中的候选人信息，生成一段自然、友好的开场白，介绍你自己和面试流程。
2. **提问**: 开场白结束后，直接提出计划中第一个环节的第一个问题。
3. **严格遵循计划**: 整场面试都需要围绕这个计划展开。

**面试计划详情如下:**
```json
{plan_str}
```

现在，请生成你的开场白，并在结尾处直接提出第一个问题。
"""
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content="你好，请开始面试吧。") # 模拟一个触发信号
        ]
        
        try:
            response = self.llm_client.chat_completion(messages)
            # LLM会返回包含开场白和第一个问题的完整文本
            initial_response = response.content
            
            self.logger.info(f"生成的包含开场白和首个问题的完整回应: {initial_response[:100]}...")
            
            # 由于LLM已经提出了第一个问题，我们需要同步状态
            self._update_state(DialogState.LISTENING)
            self.context.follow_up_count = 0 
            
            return initial_response
        except Exception as e:
            self.logger.error(f"通过LLM生成开场白失败: {e}", exc_info=True)
            # 如果LLM失败，回退到简单的问候
            return "你好，欢迎参加面试。我们现在开始吧。请问你准备好了吗？"
    
    async def _ask_current_question(self) -> str:
        """提出当前问题"""
        current_question = self._get_current_question()
        if not current_question:
            return await self._close_interview()
        
        self._update_state(DialogState.LISTENING)
        self.context.follow_up_count = 0  # 重置追问计数
        
        question_text = current_question.get("question", "")
        self.context.add_conversation("interviewer", question_text, {
            "type": "main_question",
            "question_index": self.context.current_question_index,
            "section_index": self.context.current_section_index
        })
        
        return question_text
    
    async def _generate_follow_up(self, candidate_response: str, current_question: Dict) -> str:
        """生成追问"""
        self._update_state(DialogState.FOLLOWING_UP)
        
        follow_up_data = self.llm_client.generate_follow_up(
            question=current_question.get("question", ""),
            answer=candidate_response,
            context="技术面试"
        )
        
        follow_up_question = follow_up_data.get("follow_up_question", "能否详细说明一下？")
        key_points = follow_up_data.get("key_points", [])
        
        self.context.add_conversation("interviewer", follow_up_question, {
            "type": "follow_up",
            "key_points": key_points,
            "follow_up_count": self.context.follow_up_count + 1
        })
        
        return follow_up_question
    
    async def _move_to_next_question(self) -> str:
        """移动到下一个问题"""
        # 给予简短反馈
        feedback = "谢谢您的回答。"
        
        # 移动到下一个问题
        self.context.current_question_index += 1
        
        # 检查是否需要切换到下一个环节
        current_section = self._get_current_section()
        if (current_section and 
            self.context.current_question_index >= len(current_section.get("questions", []))):
            self.context.current_section_index += 1
            self.context.current_question_index = 0
            
            # 添加环节过渡
            if self.context.current_section_index < len(self.interview_plan.get("sections", [])):
                transition = await self._generate_section_transition()
                full_response = f"{feedback}\n\n{transition}\n\n"
                next_question = await self._ask_current_question()
                return f"{full_response}{next_question}"
        
        # 继续当前环节的下一个问题
        next_question = await self._ask_current_question()
        return f"{feedback}\n\n{next_question}"
    
    async def _generate_section_transition(self) -> str:
        """生成环节过渡语"""
        next_section = self._get_current_section()
        if not next_section:
            return ""
        
        return f"好的，现在让我们进入下一个环节：{next_section.get('name', '下一环节')}。"
    
    async def _analyze_response(self, response: str, question: Dict) -> Dict:
        """分析候选人回答"""
        return self.llm_client.analyze_answer(
            question=question.get("question", ""),
            answer=response,
            evaluation_criteria=question.get("evaluation_points", [])
        )
    
    async def _ask_for_clarification(self, response: str, question: Dict) -> str:
        """请求澄清"""
        clarification_prompt = f"""
候选人对问题的回答比较简短或不够清楚：

问题：{question.get('question', '')}
回答：{response}

请生成一个友好的澄清问题，帮助候选人更充分地表达想法。
"""
        
        messages = [
            Message(role="system", content="你是一位友好的面试官。"),
            Message(role="user", content=clarification_prompt)
        ]
        
        result = self.llm_client.chat_completion(messages)
        clarification = result.content
        
        self.context.add_conversation("interviewer", clarification, {
            "type": "clarification"
        })
        
        return clarification
    
    async def _close_interview(self) -> str:
        """结束面试"""
        self._update_state(DialogState.CLOSING)
        
        closing_info = self.interview_plan.get("closing", {})
        closing_steps = closing_info.get("steps", [
            "感谢您今天的时间",
            "您的表现很不错",
            "我们会在3-5个工作日内给您反馈",
            "您还有什么问题想问吗？"
        ])
        
        closing_message = "\n".join(closing_steps)
        self.context.add_conversation("interviewer", closing_message, {
            "type": "closing"
        })
        
        self._update_state(DialogState.COMPLETED)
        return closing_message
    
    def _get_current_section(self) -> Optional[Dict]:
        """获取当前环节"""
        sections = self.interview_plan.get("sections", [])
        if self.context.current_section_index < len(sections):
            return sections[self.context.current_section_index]
        return None
    
    def _get_current_question(self) -> Optional[Dict]:
        """获取当前问题"""
        current_section = self._get_current_section()
        if not current_section:
            return None
        
        questions = current_section.get("questions", [])
        if self.context.current_question_index < len(questions):
            return questions[self.context.current_question_index]
        return None
    
    def _update_state(self, new_state: DialogState):
        """更新对话状态"""
        old_state = self.context.current_state
        self.context.current_state = new_state
        
        self.logger.info(f"对话状态变更: {old_state.value} -> {new_state.value}")
        
        if self.on_state_change:
            self.on_state_change(old_state, new_state)
    
    def get_conversation_summary(self) -> Dict:
        """获取对话摘要"""
        return {
            "total_exchanges": len(self.context.conversation_history),
            "current_state": self.context.current_state.value,
            "current_progress": {
                "section": self.context.current_section_index,
                "question": self.context.current_question_index
            },
            "supervisor_interventions": len([
                msg for msg in self.context.conversation_history 
                if msg.get("metadata", {}).get("type") == "supervisor_intervention"
            ])
        } 
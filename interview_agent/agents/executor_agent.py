"""
ExecutorAgent - 执行面试流程
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime
from enum import Enum
import json

from ..core.base_agent import BaseAgent, AgentContext, MessageType, AgentMessage
from ..core.llm_client import WildcardLLMClient, Message
from ..core.realtime_voice_adapter import VoiceInterviewSession
from config.settings import settings

# 条件导入AudioManager
try:
    from ..core.audio_handler import AudioManager
    AUDIO_HANDLER_AVAILABLE = True
except ImportError:
    AudioManager = None
    AUDIO_HANDLER_AVAILABLE = False


class InterviewState(Enum):
    """面试状态枚举"""
    NOT_STARTED = "not_started"
    WARMUP = "warmup"
    IN_PROGRESS = "in_progress"
    CLOSING = "closing"
    ENDED = "ended"
    PAUSED = "paused"


class ConversationTurn:
    """面试对话轮次"""
    def __init__(self, speaker: str, content: str, timestamp: str):
        self.speaker = speaker
        self.content = content
        self.timestamp = timestamp
    
    def to_dict(self):
        """转换为字典"""
        return {
            "speaker": self.speaker,
            "content": self.content,
            "timestamp": self.timestamp
        }


class ExecutorAgent(BaseAgent):
    """执行Agent - 执行面试流程，具备语音交互能力"""
    
    def __init__(self, 
                 name: str = "ExecutorAgent",
                 audio_handler_type: str = "edge",
                 enable_voice: bool = True,
                 use_realtime_voice: bool = False,
                 **kwargs):
        super().__init__(name, description="执行面试流程", **kwargs)
        self.llm = WildcardLLMClient(
            api_key=settings.wildcard_api_key,
            api_base=settings.wildcard_api_base,
            model=settings.llm_model,
            temperature=settings.executor_temperature,
            max_tokens=settings.executor_max_tokens
        )
        self.enable_voice = enable_voice
        self.use_realtime_voice = use_realtime_voice
        
        # 初始化音频处理
        if enable_voice and not use_realtime_voice and AUDIO_HANDLER_AVAILABLE:
            self.audio_manager = AudioManager(audio_handler_type, **kwargs)
        else:
            self.audio_manager = None
            if enable_voice and not use_realtime_voice and not AUDIO_HANDLER_AVAILABLE:
                self.logger.warning("传统音频处理不可用，建议使用实时语音模式")
        
        # 语音面试会话（新增）
        self.voice_session: Optional[VoiceInterviewSession] = None
        
        # 面试状态
        self.state = InterviewState.NOT_STARTED
        self.current_section_index = 0
        self.current_question_index = 0
        self.conversation_history: List[ConversationTurn] = []
        
        # 监督员指令队列
        self.supervisor_instructions: asyncio.Queue = asyncio.Queue()
        
        # 回调函数
        self.on_state_change: Optional[Callable] = None
        self.on_conversation_update: Optional[Callable] = None
    
    async def start(self, context: AgentContext) -> AgentContext:
        """启动执行器，作为 process 的别名，用于更清晰的启动流程"""
        return await self.process(context)
    
    async def process(self, context: AgentContext) -> AgentContext:
        """处理面试执行任务"""
        try:
            # 获取面试计划
            interview_plan = context.get_variable("interview_plan")
            if not interview_plan:
                raise ValueError("缺少面试计划")
            
            self.add_message(context, "开始执行面试...", MessageType.SYSTEM)
            
            # 检查是否使用实时语音模式
            if self.use_realtime_voice:
                return await self._execute_realtime_voice_interview(interview_plan, context)
            else:
                return await self._execute_traditional_interview(interview_plan, context)
            
        except Exception as e:
            self.logger.error(f"面试执行失败: {e}")
            raise
    
    async def _execute_realtime_voice_interview(self, interview_plan: Dict[str, Any], context: AgentContext) -> AgentContext:
        """执行实时语音面试"""
        try:
            self.logger.info("启动实时语音面试模式")
            
            # 获取候选人信息
            candidate_info = interview_plan.get("candidate_info", {})
            candidate_name = candidate_info.get("name", "候选人")
            
            # 创建语音面试会话
            self.voice_session = VoiceInterviewSession(
                llm_client=self.llm,
                interview_plan=interview_plan,
                candidate_name=candidate_name
            )
            
            # 启动语音面试
            result = await self.voice_session.start_interview()
            
            if result["status"] == "success":
                self.add_message(context, "实时语音面试已启动", MessageType.SYSTEM)
                
                # 保存会话信息到上下文
                context.set_variable("voice_session", self.voice_session)
                context.set_variable("interview_mode", "realtime_voice")
                
                # 这里可以添加等待面试完成的逻辑
                # 或者返回让外部控制面试流程
                
            else:
                raise Exception(f"启动语音面试失败: {result['message']}")
            
            return context
            
        except Exception as e:
            self.logger.error(f"实时语音面试执行失败: {e}")
            raise
    
    async def _execute_traditional_interview(self, interview_plan: Dict[str, Any], context: AgentContext) -> AgentContext:
        """执行传统面试流程"""
        # 设置系统指令
        system_instruction = await self._generate_system_instruction(interview_plan)
        
        # 执行面试流程
        await self._execute_interview(interview_plan, system_instruction, context)
        
        # 保存对话记录
        interview_record = await self._save_conversation_record()
        
        # 更新上下文
        context.set_variable("conversation_history", [turn.to_dict() for turn in self.conversation_history])
        context.set_variable("interview_record_file", interview_record)
        context.add_file("interview_record", interview_record)
        
        self.add_message(
            context,
            f"面试已完成，对话记录已保存至: {interview_record}",
            MessageType.SYSTEM
        )
        
        return context
    
    async def _generate_system_instruction(self, interview_plan: Dict[str, Any]) -> str:
        """生成面试官系统指令"""
        return f"""你是一位专业的技术面试官，正在进行算法工程师岗位的面试。

面试计划概览：
- 候选人：{interview_plan['candidate_info']['name']}
- 总时长：{interview_plan['total_duration_minutes']}分钟
- 环节数：{len(interview_plan['sections'])}个

你的职责：
1. 按照面试计划进行，但保持灵活性
2. 根据候选人的回答进行适当的追问
3. 保持专业和友善的态度
4. 控制好时间节奏
5. 如果候选人的回答不清晰，请礼貌地要求澄清
6. 在适当的时候给予鼓励和认可

注意事项：
- 不要一次问多个问题
- 给候选人充分的思考和回答时间
- 保持对话的自然流畅
- 如果候选人表现出困难，可以给予适当的提示"""
    
    async def _execute_interview(self, 
                               interview_plan: Dict[str, Any],
                               system_instruction: str,
                               context: AgentContext):
        """执行面试流程"""
        
        # 开始面试
        self.state = InterviewState.WARMUP
        await self._notify_state_change()
        
        # 执行开场
        await self._execute_warmup(interview_plan['warmup'], system_instruction)
        
        # 执行正式面试环节
        self.state = InterviewState.IN_PROGRESS
        await self._notify_state_change()
        
        for i, section in enumerate(interview_plan['sections']):
            self.current_section_index = i
            await self._execute_section(section, system_instruction)
            
            # 检查是否需要提前结束
            if self.state == InterviewState.ENDED:
                break
        
        # 执行结束环节
        if self.state != InterviewState.ENDED:
            self.state = InterviewState.CLOSING
            await self._notify_state_change()
            await self._execute_closing(interview_plan['closing'], system_instruction)
        
        # 面试结束
        self.state = InterviewState.ENDED
        await self._notify_state_change()
    
    async def _execute_warmup(self, warmup: Dict[str, Any], system_instruction: str):
        """执行开场环节"""
        self.logger.info("执行面试开场")
        
        # 执行开场步骤
        for step in warmup['steps']:
            if "面试官" in step or "介绍" in step:
                # 面试官说话
                await self._interviewer_speak(step)
            elif "候选人" in step and "自我介绍" in step:
                # 请求自我介绍
                await self._interviewer_speak(step)
                response = await self._candidate_respond()
                
                # 基于自我介绍生成破冰问题
                icebreaker = await self._generate_icebreaker(response)
                if icebreaker:
                    await self._interviewer_speak(icebreaker)
                    await self._candidate_respond()
    
    async def _execute_section(self, section: Dict[str, Any], system_instruction: str):
        """执行面试环节"""
        self.logger.info(f"执行面试环节: {section['name']}")
        
        # 介绍环节
        intro = f"好的，接下来我们进入{section['name']}环节。{section['description']}"
        await self._interviewer_speak(intro)
        
        # 执行每个问题
        for i, question in enumerate(section['questions']):
            self.current_question_index = i
            await self._execute_question(question, system_instruction)
            
            # 检查监督员指令
            await self._check_supervisor_instructions()
    
    async def _execute_question(self, question: Dict[str, Any], system_instruction: str):
        """执行单个问题"""
        # 提问
        await self._interviewer_speak(question['question'])
        
        # 候选人回答
        answer = await self._candidate_respond()
        
        # 分析回答并决定是否追问
        should_followup = await self._analyze_answer(question, answer)
        
        if should_followup and question.get('follow_up_questions'):
            # 选择追问
            followup = await self._select_followup(
                question['follow_up_questions'],
                answer,
                system_instruction
            )
            if followup:
                await self._interviewer_speak(followup)
                await self._candidate_respond()
    
    async def _execute_closing(self, closing: Dict[str, Any], system_instruction: str):
        """执行结束环节"""
        self.logger.info("执行面试结束环节")
        
        for step in closing['steps']:
            if "候选人" in step and "提问" in step:
                await self._interviewer_speak(step)
                questions = await self._candidate_respond()
                
                # 回答候选人的问题
                if questions and "？" in questions:
                    answer = await self._generate_answer_to_candidate(questions)
                    await self._interviewer_speak(answer)
            else:
                await self._interviewer_speak(step)
    
    async def _interviewer_speak(self, text: str):
        """面试官说话"""
        self.conversation_history.append(ConversationTurn("面试官", text, datetime.now().isoformat()))
        
        if self.enable_voice and self.audio_manager:
            await self.audio_manager.speak(text, voice="professional")
        
        await self._notify_conversation_update()
    
    async def _candidate_respond(self) -> str:
        """候选人回答"""
        if self.enable_voice and self.audio_manager:
            # 语音输入
            response = await self.audio_manager.listen()
        else:
            # 文本输入（模拟）
            response = await self._get_text_input()
        
        self.conversation_history.append(ConversationTurn("候选人", response, datetime.now().isoformat()))
        await self._notify_conversation_update()
        
        return response
    
    async def _get_text_input(self) -> str:
        """获取文本输入（用于测试或非语音模式）"""
        # 这里应该连接到Gradio的输入
        # 暂时返回模拟回答
        await asyncio.sleep(1)
        return "这是候选人的回答..."
    
    async def _check_supervisor_instructions(self):
        """检查并处理监督员指令"""
        try:
            while not self.supervisor_instructions.empty():
                instruction = await self.supervisor_instructions.get()
                self.logger.info(f"收到监督员指令: {instruction}")
                
                # 将指令融入对话
                await self._process_supervisor_instruction(instruction)
        except Exception as e:
            self.logger.error(f"处理监督员指令失败: {e}")
    
    async def _process_supervisor_instruction(self, instruction: str):
        """处理监督员指令"""
        # 生成基于指令的追问
        prompt = f"""基于以下监督员指令，生成一个自然的追问或调整：

监督员指令：{instruction}

最近的对话：
{self._get_recent_conversation(3)}

请生成一个自然的追问，要符合面试的语境。"""

        messages = [
            Message(role="system", content="你是面试官，需要根据指令调整面试方向。"),
            Message(role="user", content=prompt)
        ]
        
        response = self.llm.chat_completion(messages)
        
        # 执行追问
        await self._interviewer_speak(response.content)
        await self._candidate_respond()
    
    async def _generate_icebreaker(self, self_intro: str) -> Optional[str]:
        """基于自我介绍生成破冰问题"""
        prompt = f"""基于候选人的自我介绍，生成一个轻松的破冰问题：

自我介绍：{self_intro}

请生成一个友好、轻松的问题，帮助缓解面试氛围。"""

        messages = [
            Message(role="system", content="你是友善的面试官。"),
            Message(role="user", content=prompt)
        ]
        
        response = self.llm.chat_completion(messages)
        return response.content
    
    async def _analyze_answer(self, question: Dict[str, Any], answer: str) -> bool:
        """分析回答，决定是否需要追问"""
        if len(answer) < 20:  # 回答太短
            return True
        
        # 使用LLM分析
        prompt = f"""分析候选人的回答是否完整和清晰：

问题：{question['question']}
回答：{answer}
考察点：{', '.join(question.get('evaluation_points', []))}

请判断是否需要追问（回答yes或no）。"""

        messages = [
            Message(role="system", content="你是面试评估专家。"),
            Message(role="user", content=prompt)
        ]
        
        response = self.llm.chat_completion(messages)
        return "yes" in response.content.lower()
    
    async def _select_followup(self, 
                             followup_questions: List[str], 
                             answer: str,
                             system_instruction: str) -> Optional[str]:
        """选择合适的追问"""
        prompt = f"""基于候选人的回答，选择或生成一个合适的追问：

候选人回答：{answer}

可选的追问方向：
{chr(10).join(f"- {q}" for q in followup_questions)}

请选择最合适的追问，或基于这些方向生成一个新的追问。"""

        messages = [
            Message(role="system", content=system_instruction),
            Message(role="user", content=prompt)
        ]
        
        response = self.llm.chat_completion(messages)
        return response.content
    
    async def _generate_answer_to_candidate(self, questions: str) -> str:
        """回答候选人的问题"""
        prompt = f"""候选人提出了以下问题：

{questions}

请以面试官的身份，专业、友善地回答这些问题。可以谈论：
- 公司文化和团队氛围
- 技术栈和项目方向
- 职业发展机会
- 工作方式等

保持回答的真实性，不要过度承诺。"""

        messages = [
            Message(role="system", content="你是公司的技术面试官。"),
            Message(role="user", content=prompt)
        ]
        
        response = self.llm.chat_completion(messages)
        return response.content
    
    def _get_recent_conversation(self, n: int) -> str:
        """获取最近的n轮对话"""
        recent = self.conversation_history[-n*2:] if len(self.conversation_history) >= n*2 else self.conversation_history
        return "\n".join([f"{turn.speaker}: {turn.content}" for turn in recent])
    
    async def _save_conversation_record(self) -> Path:
        """保存对话记录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"interview_record_{timestamp}.md")
        
        # 生成记录文档
        record_md = self._generate_record_markdown()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(record_md)
        
        return output_path
    
    def _generate_record_markdown(self) -> str:
        """生成面试记录Markdown文档"""
        md_lines = ["# 面试对话记录\n"]
        md_lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md_lines.append("---\n")
        
        # 对话记录
        md_lines.append("## 对话详情\n")
        
        current_section = ""
        for turn in self.conversation_history:
            # 标记环节转换
            if "接下来我们进入" in turn.content and turn.speaker == "面试官":
                current_section = turn.content.split("进入")[1].split("环节")[0]
                md_lines.append(f"\n### {current_section}\n")
            
            # 记录对话
            time_str = turn.timestamp.split("T")[1].split(".")[0]
            md_lines.append(f"**[{time_str}] {turn.speaker}**：{turn.content}\n")
        
        # 统计信息
        md_lines.append("\n---\n")
        md_lines.append("## 统计信息\n")
        md_lines.append(f"- 总对话轮数：{len(self.conversation_history)}")
        md_lines.append(f"- 面试官发言：{sum(1 for t in self.conversation_history if t.speaker == '面试官')}次")
        md_lines.append(f"- 候选人发言：{sum(1 for t in self.conversation_history if t.speaker == '候选人')}次")
        
        total_duration = (datetime.fromisoformat(self.conversation_history[-1].timestamp) - datetime.fromisoformat(self.conversation_history[0].timestamp)).total_seconds() / 60 if len(self.conversation_history) > 1 else 0
        md_lines.append(f"- 总时长：{total_duration:.1f}分钟\n")
        
        return "\n".join(md_lines)
    
    async def _notify_state_change(self):
        """通知状态变化"""
        if self.on_state_change:
            await self.on_state_change(self.state)
    
    async def _notify_conversation_update(self):
        """通知对话更新"""
        if self.on_conversation_update:
            await self.on_conversation_update(self.conversation_history)
    
    async def add_supervisor_instruction(self, instruction: str):
        """添加监督员指令"""
        if self.use_realtime_voice and self.voice_session:
            # 实时语音模式下，直接发送给语音会话
            return await self.voice_session.add_supervisor_instruction(instruction)
        else:
            # 传统模式下，添加到队列
            await self.supervisor_instructions.put(instruction)
    
    def pause_interview(self):
        """暂停面试"""
        if self.state == InterviewState.IN_PROGRESS:
            self.state = InterviewState.PAUSED
    
    def resume_interview(self):
        """恢复面试"""
        if self.state == InterviewState.PAUSED:
            self.state = InterviewState.IN_PROGRESS
    
    def end_interview(self):
        """结束面试"""
        self.state = InterviewState.ENDED 
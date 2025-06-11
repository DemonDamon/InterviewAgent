"""
面试执行模块 - 管理面试流程和对话
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from interview_agent.core.resume_parser import CandidateProfile
from interview_agent.core.question_generator import InterviewQuestion, QuestionType
from interview_agent.core.llm_client import WildcardLLMClient


class InterviewState(Enum):
    """面试状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MessageRole(Enum):
    """消息角色"""
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"
    SYSTEM = "system"


@dataclass
class Message:
    """对话消息"""
    id: str
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)


@dataclass
class InterviewSession:
    """面试会话"""
    id: str
    candidate_profile: CandidateProfile
    questions: List[InterviewQuestion]
    state: InterviewState = InterviewState.NOT_STARTED
    messages: List[Message] = field(default_factory=list)
    current_question_index: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    evaluations: Dict = field(default_factory=dict)
    
    def get_current_question(self) -> Optional[InterviewQuestion]:
        """获取当前题目"""
        if 0 <= self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None
    
    def add_message(self, role: MessageRole, content: str, metadata: Dict = None):
        """添加消息"""
        message = Message(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        self.messages.append(message)
        return message


class InterviewConductor:
    """面试执行器"""
    
    def __init__(self, llm_client=None):
        """
        初始化面试执行器
        
        Args:
            llm_client: LLM客户端实例，如果为None则需要在使用前设置
        """
        self.llm_client = llm_client
        self.sessions: Dict[str, InterviewSession] = {}
        self.prompts = self._load_prompts()
    
    def _load_prompts(self) -> Dict:
        """加载提示词模板"""
        return {
            "greeting": """你好，{name}！欢迎参加今天的技术面试。我是您的面试官。
今天的面试大约需要{duration}分钟，主要包括以下几个部分：
1. 算法题目
2. 工程实践问题
3. 技术深度探讨
4. 行为面试

在面试过程中，如果有任何问题需要澄清，请随时告诉我。
现在我们开始第一个问题。""",
            
            "question_intro": """接下来是{question_type}题目：
{question}

请您详细说明您的思路和解决方案。""",
            
            "follow_up": """很好，关于您刚才的回答，我想进一步了解：
{follow_up_question}""",
            
            "encouragement": [
                "很好的思路，请继续。",
                "这是一个不错的方向，能详细说说吗？",
                "有意思的观点，可以展开讲讲您的想法吗？"
            ],
            
            "clarification": [
                "能否举个具体的例子来说明？",
                "您提到的{concept}，能详细解释一下吗？",
                "在实际项目中，您是如何应用这个方案的？"
            ],
            
            "transition": """感谢您的回答。让我们继续下一个问题。""",
            
            "closing": """非常感谢您今天的时间，{name}。
面试到此结束。您的表现{performance_summary}。
我们会在{timeline}内给您反馈。
您有什么问题想问我吗？"""
        }
    
    def create_session(self, 
                      candidate_profile: CandidateProfile,
                      questions: List[InterviewQuestion]) -> InterviewSession:
        """创建面试会话"""
        session = InterviewSession(
            id=str(uuid.uuid4()),
            candidate_profile=candidate_profile,
            questions=questions
        )
        self.sessions[session.id] = session
        return session
    
    def start_interview(self, session_id: str) -> str:
        """开始面试"""
        if not self.llm_client:
            raise ValueError("LLM客户端未设置，请确保在使用前设置LLM客户端")
            
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.state = InterviewState.IN_PROGRESS
        session.start_time = datetime.now()
        
        # 生成开场白
        greeting = self.prompts["greeting"].format(
            name=session.candidate_profile.name,
            duration=sum(q.time_minutes for q in session.questions)
        )
        
        session.add_message(MessageRole.INTERVIEWER, greeting)
        
        # 提出第一个问题
        first_question_msg = self._format_question(session.get_current_question())
        session.add_message(MessageRole.INTERVIEWER, first_question_msg)
        
        return greeting + "\n\n" + first_question_msg
    
    def process_candidate_response(self, 
                                 session_id: str, 
                                 response: str) -> Tuple[str, bool]:
        """处理候选人回答"""
        if not self.llm_client:
            raise ValueError("LLM客户端未设置，请确保在使用前设置LLM客户端")
            
        session = self.sessions.get(session_id)
        if not session or session.state != InterviewState.IN_PROGRESS:
            raise ValueError(f"Invalid session state")
        
        # 记录候选人回答
        session.add_message(MessageRole.CANDIDATE, response)
        
        current_question = session.get_current_question()
        if not current_question:
            return self._end_interview(session)
        
        # 使用LLM分析回答
        analysis = self._analyze_response_with_llm(response, current_question)
        
        # 根据分析结果生成回应
        if analysis.get("needs_clarification"):
            # 需要澄清
            clarification = self._generate_clarification_with_llm(response, current_question)
            session.add_message(MessageRole.INTERVIEWER, clarification)
            return clarification, False
        
        elif analysis.get("follow_up_needed") and current_question.follow_up_questions:
            # 使用LLM生成追问
            follow_up = self.llm_client.generate_follow_up(
                question=current_question.question,
                answer=response,
                context="技术面试"
            )
            follow_up_msg = self.prompts["follow_up"].format(follow_up_question=follow_up)
            session.add_message(MessageRole.INTERVIEWER, follow_up_msg)
            return follow_up_msg, False
        
        else:
            # 进入下一题
            # 先给予反馈
            feedback = analysis.get("feedback", "谢谢您的回答。")
            session.add_message(MessageRole.INTERVIEWER, feedback)
            
            # 记录评估
            session.evaluations[current_question.id] = {
                "response": response,
                "analysis": analysis,
                "score": analysis.get("score", 0)
            }
            
            # 移动到下一题
            session.current_question_index += 1
            next_question = session.get_current_question()
            
            if next_question:
                transition = self.prompts["transition"]
                next_question_msg = self._format_question(next_question)
                full_response = f"{feedback}\n\n{transition}\n\n{next_question_msg}"
                session.add_message(MessageRole.INTERVIEWER, f"{transition}\n\n{next_question_msg}")
                return full_response, False
            else:
                # 面试结束
                return self._end_interview(session)
    
    def _format_question(self, question: InterviewQuestion) -> str:
        """格式化题目"""
        question_type_map = {
            QuestionType.ALGORITHM: "算法",
            QuestionType.ENGINEERING: "工程实践",
            QuestionType.OPEN_ENDED: "开放性",
            QuestionType.BEHAVIORAL: "行为面试",
            QuestionType.SYSTEM_DESIGN: "系统设计"
        }
        
        return self.prompts["question_intro"].format(
            question_type=question_type_map.get(question.type, ""),
            question=question.question
        )
    
    def _analyze_response_with_llm(self, response: str, question: InterviewQuestion) -> Dict:
        """使用LLM分析候选人回答"""
        return self.llm_client.analyze_answer(
            question=question.question,
            answer=response,
            evaluation_criteria=question.evaluation_criteria or []
        )
    
    def _generate_clarification_with_llm(self, response: str, question: InterviewQuestion) -> str:
        """使用LLM生成澄清问题"""
        prompt = f"""候选人的回答比较简短或不够清楚，请生成一个友好的澄清问题：

原问题：{question.question}
候选人回答：{response}

请生成一个鼓励性的引导问题，帮助候选人更充分地表达他们的想法。"""

        result = self.llm_client.chat_completion([
            {"role": "system", "content": "你是一位友好的技术面试官。"},
            {"role": "user", "content": prompt}
        ])
        
        return result.content
    
    def _end_interview(self, session: InterviewSession) -> Tuple[str, bool]:
        """结束面试"""
        session.state = InterviewState.COMPLETED
        session.end_time = datetime.now()
        
        # 生成总体评价
        total_score = sum(
            eval_data.get("score", 0) 
            for eval_data in session.evaluations.values()
        )
        avg_score = total_score / len(session.evaluations) if session.evaluations else 0
        
        performance_summary = "很不错" if avg_score >= 3 else "有待提高"
        
        closing = self.prompts["closing"].format(
            name=session.candidate_profile.name,
            performance_summary=performance_summary,
            timeline="3-5个工作日"
        )
        
        session.add_message(MessageRole.INTERVIEWER, closing)
        
        return closing, True
    
    def get_session_report(self, session_id: str) -> Dict:
        """获取面试报告"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        duration = None
        if session.start_time and session.end_time:
            duration = (session.end_time - session.start_time).total_seconds() / 60
        
        # 使用LLM生成综合评估
        strengths, improvements, recommendation = self._generate_comprehensive_evaluation(session)
        
        report = {
            "session_id": session.id,
            "candidate": {
                "name": session.candidate_profile.name,
                "skills": session.candidate_profile.skills,
                "experience_years": session.candidate_profile.experience_years
            },
            "duration_minutes": duration,
            "questions_asked": len(session.evaluations),
            "evaluations": session.evaluations,
            "overall_score": self._calculate_overall_score(session),
            "strengths": strengths,
            "areas_for_improvement": improvements,
            "recommendation": recommendation
        }
        
        return report
    
    def _calculate_overall_score(self, session: InterviewSession) -> float:
        """计算总分"""
        if not session.evaluations:
            return 0.0
        
        total = sum(eval_data.get("score", 0) for eval_data in session.evaluations.values())
        return total / len(session.evaluations)
    
    def _generate_comprehensive_evaluation(self, session: InterviewSession) -> Tuple[List[str], List[str], str]:
        """使用LLM生成综合评估"""
        # 准备评估数据
        eval_summary = []
        for q_id, eval_data in session.evaluations.items():
            question = next((q for q in session.questions if q.id == q_id), None)
            if question:
                eval_summary.append({
                    "question": question.question,
                    "type": question.type.value,
                    "response": eval_data.get("response", ""),
                    "score": eval_data.get("score", 0)
                })
        
        prompt = f"""基于以下面试记录，生成综合评估：

候选人：{session.candidate_profile.name}
经验：{session.candidate_profile.experience_years}年

面试表现：
{eval_summary}

请生成：
1. 主要优势（3-5条）
2. 待改进领域（2-3条）
3. 录用建议（一句话总结）

以JSON格式返回。"""

        try:
            result = self.llm_client.chat_completion([
                {"role": "system", "content": "你是一位资深的技术面试官，擅长评估候选人。"},
                {"role": "user", "content": prompt}
            ])
            
            import json
            data = json.loads(result.content)
            
            strengths = data.get("strengths", ["技术基础扎实", "沟通表达清晰"])
            improvements = data.get("improvements", ["需要加强系统设计经验"])
            recommendation = data.get("recommendation", "建议进一步评估")
            
            return strengths, improvements, recommendation
            
        except:
            # 使用默认评估
            return self._default_evaluation(session)
    
    def _default_evaluation(self, session: InterviewSession) -> Tuple[List[str], List[str], str]:
        """默认评估（当LLM调用失败时）"""
        score = self._calculate_overall_score(session)
        
        if score >= 4:
            return (
                ["算法基础扎实", "工程经验丰富", "学习能力强"],
                ["可以进一步提升系统设计能力"],
                "强烈推荐：候选人表现优秀，建议进入下一轮"
            )
        elif score >= 3:
            return (
                ["基础知识掌握较好", "有一定项目经验"],
                ["算法能力需要加强", "缺少大规模系统经验"],
                "推荐：候选人基础不错，建议进一步考察"
            )
        else:
            return (
                ["学习态度积极", "有发展潜力"],
                ["技术深度不足", "项目经验欠缺", "需要更多实践"],
                "暂不推荐：候选人需要更多经验积累"
            ) 
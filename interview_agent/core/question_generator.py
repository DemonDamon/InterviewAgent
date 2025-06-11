"""
面试题目生成模块 - 基于候选人背景生成定制化面试题
"""

import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from interview_agent.core.resume_parser import CandidateProfile
from interview_agent.core.llm_client import WildcardLLMClient, Message


class QuestionType(Enum):
    """题目类型"""
    ALGORITHM = "algorithm"  # 算法题
    SYSTEM_DESIGN = "system_design"  # 系统设计
    ENGINEERING = "engineering"  # 工程实践
    OPEN_ENDED = "open_ended"  # 开放性问题
    BEHAVIORAL = "behavioral"  # 行为面试


@dataclass
class InterviewQuestion:
    """面试题目"""
    id: str
    type: QuestionType
    question: str
    difficulty: int  # 1-5
    expected_answer: Optional[str] = None
    evaluation_criteria: List[str] = None
    follow_up_questions: List[str] = None
    time_minutes: int = 10
    
    def __post_init__(self):
        if self.evaluation_criteria is None:
            self.evaluation_criteria = []
        if self.follow_up_questions is None:
            self.follow_up_questions = []


@dataclass
class JobDescription:
    """职位描述"""
    title: str
    department: str = ""
    requirements: List[str] = None
    responsibilities: List[str] = None
    nice_to_have: List[str] = None
    
    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []
        if self.responsibilities is None:
            self.responsibilities = []
        if self.nice_to_have is None:
            self.nice_to_have = []
    
    def to_text(self) -> str:
        """转换为文本描述"""
        text = f"职位：{self.title}\n"
        if self.department:
            text += f"部门：{self.department}\n"
        
        if self.requirements:
            text += "\n岗位要求：\n"
            for req in self.requirements:
                text += f"- {req}\n"
        
        if self.responsibilities:
            text += "\n工作职责：\n"
            for resp in self.responsibilities:
                text += f"- {resp}\n"
        
        if self.nice_to_have:
            text += "\n加分项：\n"
            for item in self.nice_to_have:
                text += f"- {item}\n"
        
        return text


class QuestionGenerator:
    """题目生成器"""
    
    def __init__(self, llm_client=None):
        """
        初始化题目生成器
        
        Args:
            llm_client: LLM客户端实例，如果为None则需要在使用前设置
        """
        self.llm_client = llm_client
    
    def generate_interview_plan(self, 
                               profile: CandidateProfile,
                               job_description: JobDescription,
                               interviewer_requirements: str = "",
                               duration_minutes: int = 30,
                               focus_areas: Optional[List[str]] = None) -> List[InterviewQuestion]:
        """生成面试计划"""
        
        if not self.llm_client:
            raise ValueError("LLM客户端未设置，请确保在使用前设置LLM客户端")
            
        # 准备候选人信息
        candidate_info = self._format_candidate_info(profile)
        
        # 准备职位描述
        jd_text = job_description.to_text()
        
        # 额外要求
        if focus_areas:
            interviewer_requirements += f"\n重点考察领域：{', '.join(focus_areas)}"
        
        # 调用LLM生成题目
        questions_json = self.llm_client.generate_interview_questions(
            candidate_info=candidate_info,
            job_description=jd_text,
            interview_requirements=interviewer_requirements,
            duration_minutes=duration_minutes
        )
        
        # 解析生成的题目
        try:
            questions_data = json.loads(questions_json)
            return self._parse_questions(questions_data)
        except json.JSONDecodeError:
            # 如果解析失败，使用备用方案
            return self._generate_fallback_questions(profile, duration_minutes)
    
    def _format_candidate_info(self, profile: CandidateProfile) -> str:
        """格式化候选人信息"""
        info = f"姓名：{profile.name}\n"
        info += f"工作经验：{profile.experience_years}年\n"
        
        if profile.skills:
            info += f"技能：{', '.join(profile.skills[:15])}\n"
        
        if profile.education:
            info += "\n教育经历：\n"
            for edu in profile.education[:2]:
                info += f"- {edu}\n"
        
        if profile.work_experience:
            info += "\n工作经历：\n"
            for exp in profile.work_experience[:3]:
                info += f"- {exp}\n"
        
        if profile.projects:
            info += "\n项目经历：\n"
            for proj in profile.projects[:3]:
                info += f"- {proj}\n"
        
        return info
    
    def _parse_questions(self, questions_data: Dict) -> List[InterviewQuestion]:
        """解析LLM生成的题目"""
        questions = []
        
        # 处理不同的JSON结构
        if isinstance(questions_data, dict):
            if "questions" in questions_data:
                questions_list = questions_data["questions"]
            elif "题目" in questions_data:
                questions_list = questions_data["题目"]
            else:
                questions_list = [questions_data]
        elif isinstance(questions_data, list):
            questions_list = questions_data
        else:
            questions_list = []
        
        for i, q_data in enumerate(questions_list):
            try:
                # 提取题目信息
                question_text = q_data.get("question") or q_data.get("题目") or q_data.get("content", "")
                
                # 判断题目类型
                q_type = self._infer_question_type(question_text, q_data)
                
                # 创建题目对象
                question = InterviewQuestion(
                    id=f"q_{i+1}",
                    type=q_type,
                    question=question_text,
                    difficulty=q_data.get("difficulty", 3),
                    time_minutes=q_data.get("time", 10),
                    expected_answer=q_data.get("expected_answer", ""),
                    evaluation_criteria=q_data.get("evaluation_criteria", []),
                    follow_up_questions=q_data.get("follow_up", [])
                )
                
                questions.append(question)
                
            except Exception as e:
                print(f"解析题目时出错: {e}")
                continue
        
        return questions
    
    def _infer_question_type(self, question_text: str, q_data: Dict) -> QuestionType:
        """推断题目类型"""
        q_type_str = q_data.get("type", "").lower()
        
        if q_type_str in ["algorithm", "算法"]:
            return QuestionType.ALGORITHM
        elif q_type_str in ["engineering", "工程", "实践"]:
            return QuestionType.ENGINEERING
        elif q_type_str in ["open", "开放", "ai"]:
            return QuestionType.OPEN_ENDED
        elif q_type_str in ["behavioral", "行为", "软技能"]:
            return QuestionType.BEHAVIORAL
        elif q_type_str in ["system", "系统设计"]:
            return QuestionType.SYSTEM_DESIGN
        
        # 基于内容推断
        question_lower = question_text.lower()
        if any(keyword in question_lower for keyword in ["算法", "复杂度", "排序", "搜索", "动态规划"]):
            return QuestionType.ALGORITHM
        elif any(keyword in question_lower for keyword in ["项目", "实践", "部署", "优化", "性能"]):
            return QuestionType.ENGINEERING
        elif any(keyword in question_lower for keyword in ["ai", "机器学习", "深度学习", "rag", "agent"]):
            return QuestionType.OPEN_ENDED
        elif any(keyword in question_lower for keyword in ["团队", "挑战", "冲突", "压力", "合作"]):
            return QuestionType.BEHAVIORAL
        else:
            return QuestionType.OPEN_ENDED
    
    def _generate_fallback_questions(self, profile: CandidateProfile, duration_minutes: int) -> List[InterviewQuestion]:
        """生成备用题目（当LLM调用失败时）"""
        questions = []
        
        # 算法题
        if duration_minutes >= 20:
            questions.append(InterviewQuestion(
                id="algo_1",
                type=QuestionType.ALGORITHM,
                question="请实现一个LRU缓存，支持get和put操作，要求时间复杂度O(1)",
                difficulty=3,
                time_minutes=15,
                evaluation_criteria=["算法正确性", "时间复杂度分析", "代码质量"],
                follow_up_questions=["如何处理并发访问？", "如何实现缓存过期机制？"]
            ))
        
        # 工程题
        questions.append(InterviewQuestion(
            id="eng_1",
            type=QuestionType.ENGINEERING,
            question="请描述您在之前项目中如何处理高并发场景的经验",
            difficulty=3,
            time_minutes=10,
            evaluation_criteria=["实践经验", "问题分析能力", "技术方案合理性"]
        ))
        
        # AI开放题
        if "ai" in str(profile.skills).lower() or "机器学习" in str(profile.skills):
            questions.append(InterviewQuestion(
                id="ai_1",
                type=QuestionType.OPEN_ENDED,
                question="请谈谈您对RAG技术的理解，以及如何构建一个生产级的RAG系统",
                difficulty=4,
                time_minutes=10,
                evaluation_criteria=["技术理解深度", "系统设计能力", "实践经验"]
            ))
        
        # 行为面试题
        questions.append(InterviewQuestion(
            id="beh_1",
            type=QuestionType.BEHAVIORAL,
            question="请描述一个您在项目中遇到的最大技术挑战，以及您是如何解决的",
            difficulty=2,
            time_minutes=5,
            evaluation_criteria=["问题解决能力", "沟通表达", "学习能力"]
        ))
        
        return questions
    
    def generate_dynamic_question(self,
                                profile: CandidateProfile,
                                question_type: QuestionType,
                                context: str = "") -> InterviewQuestion:
        """动态生成单个题目"""
        
        prompt = f"""请为以下候选人生成一道{question_type.value}类型的面试题：

候选人技能：{', '.join(profile.skills[:10])}
工作经验：{profile.experience_years}年
上下文：{context}

请生成：
1. 题目内容
2. 难度（1-5）
3. 预计时间（分钟）
4. 评估要点（3-5个）
5. 参考答案要点

以JSON格式返回。"""

        response = self.llm_client.chat_completion([
            {"role": "system", "content": "你是一位技术面试官。"},
            {"role": "user", "content": prompt}
        ])
        
        try:
            data = json.loads(response.content)
            return InterviewQuestion(
                id=f"dynamic_{question_type.value}",
                type=question_type,
                question=data.get("question", ""),
                difficulty=data.get("difficulty", 3),
                time_minutes=data.get("time", 10),
                expected_answer=data.get("answer", ""),
                evaluation_criteria=data.get("criteria", [])
            )
        except:
            # 返回默认题目
            return self._generate_fallback_questions(profile, 10)[0] 
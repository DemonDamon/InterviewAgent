"""
PlannerAgent - 规划面试流程
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json

from ..core.base_agent import BaseAgent, AgentContext, MessageType
from ..core.llm_client import llm_client, Message


class InterviewSection:
    """面试环节"""
    def __init__(self, name: str, description: str, duration_minutes: int, questions: List[Dict[str, Any]]):
        self.name = name
        self.description = description
        self.duration_minutes = duration_minutes
        self.questions = questions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "duration_minutes": self.duration_minutes,
            "questions": self.questions
        }


class InterviewPlan:
    """面试计划"""
    def __init__(self):
        self.candidate_info: Dict[str, Any] = {}
        self.warmup: Dict[str, Any] = {}
        self.sections: List[InterviewSection] = []
        self.closing: Dict[str, Any] = {}
        self.total_duration_minutes: int = 0
    
    def add_section(self, section: InterviewSection):
        self.sections.append(section)
        self.calculate_total_duration()
    
    def calculate_total_duration(self):
        """计算总时长"""
        self.total_duration_minutes = sum(s.duration_minutes for s in self.sections)
        if self.warmup:
            self.total_duration_minutes += self.warmup.get("duration_minutes", 5)
        if self.closing:
            self.total_duration_minutes += self.closing.get("duration_minutes", 5)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_info": self.candidate_info,
            "warmup": self.warmup,
            "sections": [s.to_dict() for s in self.sections],
            "closing": self.closing,
            "total_duration_minutes": self.total_duration_minutes
        }
    
    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        md_lines = ["# 面试流程规划\n"]
        md_lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 候选人信息
        md_lines.append("## 一、候选人基本信息\n")
        info = self.candidate_info
        md_lines.append(f"- **姓名**：{info.get('name', 'N/A')}")
        md_lines.append(f"- **应聘岗位**：{info.get('position', 'N/A')}")
        md_lines.append(f"- **经验年限**：{info.get('experience_years', 'N/A')}")
        md_lines.append(f"- **核心技能**：{', '.join(info.get('core_skills', []))}\n")
        
        # 面试准备
        md_lines.append("## 二、面试开场（Warm-up）\n")
        warmup = self.warmup
        md_lines.append(f"**预计时长**：{warmup.get('duration_minutes', 5)}分钟\n")
        md_lines.append("### 开场流程：")
        for step in warmup.get('steps', []):
            md_lines.append(f"1. {step}")
        md_lines.append("")
        
        # 正式面试环节
        md_lines.append("## 三、正式面试环节\n")
        md_lines.append(f"**总时长**：{sum(s.duration_minutes for s in self.sections)}分钟\n")
        
        for i, section in enumerate(self.sections, 1):
            md_lines.append(f"### {i}. {section.name}")
            md_lines.append(f"**时长**：{section.duration_minutes}分钟")
            md_lines.append(f"**描述**：{section.description}\n")
            
            md_lines.append("**问题列表**：")
            for j, q in enumerate(section.questions, 1):
                md_lines.append(f"\n#### 问题{i}.{j}：{q['question']}")
                md_lines.append(f"- **类型**：{q.get('type', '技术问题')}")
                md_lines.append(f"- **预计时间**：{q.get('duration_minutes', 5)}分钟")
                md_lines.append(f"- **考察点**：{', '.join(q.get('evaluation_points', []))}")
                
                if q.get('reference_answer'):
                    md_lines.append(f"- **参考答案要点**：\n  {q['reference_answer']}")
                
                if q.get('follow_up_questions'):
                    md_lines.append("- **追问方向**：")
                    for fu in q['follow_up_questions']:
                        md_lines.append(f"  - {fu}")
            md_lines.append("")
        
        # 面试结束
        md_lines.append("## 四、面试结束\n")
        closing = self.closing
        md_lines.append(f"**预计时长**：{closing.get('duration_minutes', 5)}分钟\n")
        md_lines.append("### 结束流程：")
        for step in closing.get('steps', []):
            md_lines.append(f"- {step}")
        md_lines.append("")
        
        # 总结
        md_lines.append("## 五、面试总结\n")
        md_lines.append(f"- **总时长**：{self.total_duration_minutes}分钟")
        md_lines.append(f"- **环节数**：{len(self.sections)}个")
        md_lines.append(f"- **总问题数**：{sum(len(s.questions) for s in self.sections)}个\n")
        
        return "\n".join(md_lines)


class PlannerAgent(BaseAgent):
    """规划Agent - 基于背景信息规划面试流程"""
    
    def __init__(self, name: str = "PlannerAgent", **kwargs):
        super().__init__(name, description="规划面试流程和问题", **kwargs)
        self.llm = llm_client
        self.default_sections = [
            "算法模型基础原理",
            "项目工程实践经验", 
            "AI前沿开放性问题",
            "候选人提问环节"
        ]
    
    async def process(self, context: AgentContext) -> AgentContext:
        """处理规划任务"""
        try:
            # 获取输入
            background_doc = context.get_variable("background_document")
            combined_resume = context.get_variable("combined_resume")
            jd_text = context.get_variable("jd_text")
            extra_requirements = context.get_variable("extra_requirements")
            max_sections = context.get_variable("max_interview_sections", 4)
            
            if not background_doc:
                raise ValueError("缺少面试背景文档")
            
            self.add_message(context, "开始规划面试流程...", MessageType.SYSTEM)
            
            # 创建面试计划
            plan = InterviewPlan()
            
            # 设置候选人信息
            plan.candidate_info = await self._extract_candidate_summary(combined_resume)
            
            # 生成开场环节
            plan.warmup = await self._generate_warmup(plan.candidate_info)
            
            # 生成面试环节
            sections = await self._generate_interview_sections(
                combined_resume,
                jd_text,
                extra_requirements,
                max_sections
            )
            
            for section_data in sections:
                section = InterviewSection(
                    name=section_data["name"],
                    description=section_data["description"],
                    duration_minutes=section_data["duration_minutes"],
                    questions=section_data["questions"]
                )
                plan.add_section(section)
            
            # 生成结束环节
            plan.closing = await self._generate_closing()
            
            # 计算总时长
            plan.calculate_total_duration()
            
            # 生成面试流程文档
            panel_md = plan.to_markdown()
            
            # 保存文档
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"interview_panel_{timestamp}.md")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(panel_md)
            
            # 更新上下文
            context.set_variable("interview_plan", plan.to_dict())
            context.set_variable("interview_panel_md", panel_md)
            context.set_variable("panel_file", output_path)
            context.add_file("panel", output_path)
            
            self.add_message(
                context,
                f"面试流程已规划完成，总时长{plan.total_duration_minutes}分钟",
                MessageType.SYSTEM
            )
            
            return context
            
        except Exception as e:
            self.logger.error(f"规划失败: {e}")
            raise
    
    async def _extract_candidate_summary(self, resume: Dict[str, Any]) -> Dict[str, Any]:
        """提取候选人摘要信息"""
        self.logger.info(f"提取候选人摘要信息，resume数据类型: {type(resume)}")
        
        # 确保resume是字典
        if resume is None:
            self.logger.error("简历数据为空")
            return {
                "name": "候选人",
                "position": "算法工程师",
                "experience_years": "未知",
                "core_skills": []
            }
            
        # 尝试获取basic_info
        basic_info = resume.get("basic_info", {})
        self.logger.info(f"获取到basic_info: {basic_info}")
        
        # 安全地获取姓名
        name = "候选人"
        if isinstance(basic_info, dict) and "name" in basic_info:
            name = basic_info["name"]
        elif isinstance(resume, dict) and "name" in resume:
            name = resume["name"]
            
        self.logger.info(f"提取到候选人姓名: {name}")
        
        # 计算经验年限
        experience_years = 0
        if "work_experience" in resume and isinstance(resume["work_experience"], list):
            for exp in resume["work_experience"]:
                if isinstance(exp, dict) and exp.get("start_date") and exp.get("end_date"):
                    try:
                        # 简单计算，实际应该解析日期
                        start_year = int(exp.get("start_date", "").split("-")[0])
                        end_year = int(exp.get("end_date", "").split("-")[0])
                        experience_years += (end_year - start_year)
                    except (ValueError, IndexError):
                        experience_years += 1
        
        # 提取核心技能
        core_skills = []
        if "skills" in resume and isinstance(resume["skills"], dict):
            skills = resume["skills"]
            if "technical" in skills and isinstance(skills["technical"], list):
                core_skills.extend(skills["technical"][:5])
            if "languages" in skills and isinstance(skills["languages"], list):
                core_skills.extend(skills["languages"][:3])
        
        return {
            "name": name,
            "position": "算法工程师",  # 从JD中提取
            "experience_years": f"{experience_years}年",
            "core_skills": core_skills
        }
    
    async def _generate_warmup(self, candidate_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成开场环节"""
        name = candidate_info.get("name", "候选人")
        
        return {
            "duration_minutes": 5,
            "steps": [
                f"面试官自我介绍：你好{name}，我是今天的面试官，负责技术面试环节",
                "候选人回应：你好面试官",
                "介绍面试流程：今天的面试大概分为以下几个环节：1）自我介绍 2）技术问题讨论 3）项目经验交流 4）开放性问题 5）你的提问时间",
                "请候选人做1-2分钟的自我介绍",
                "基于自我介绍，提出一个轻松的破冰问题，如：我看到你提到了[某个有趣的项目/爱好]，能简单分享一下吗？"
            ]
        }
    
    async def _generate_interview_sections(self,
                                         resume: Dict[str, Any],
                                         jd: str,
                                         extra_req: str,
                                         max_sections: int) -> List[Dict[str, Any]]:
        """生成面试环节"""
        self.logger.info("开始生成面试环节")
        
        # 安全处理resume
        if not isinstance(resume, dict):
            self.logger.warning(f"resume不是字典类型: {type(resume)}")
            resume = {}
            
        # 限制resume大小，避免token超限
        resume_json = json.dumps(resume, ensure_ascii=False)
        if len(resume_json) > 2000:
            self.logger.info("resume过大，进行截断")
            resume_json = resume_json[:2000] + "..."
        
        prompt = f"""基于候选人简历、岗位要求和额外要求，生成{max_sections}个面试环节。

候选人简历摘要：
{resume_json}

岗位要求：
{jd}

额外要求：
{extra_req}

请生成{max_sections}个面试环节，每个环节包括：
1. name: 环节名称
2. description: 环节描述
3. duration_minutes: 预计时长（分钟）
4. questions: 问题列表，每个问题包括：
   - question: 问题内容
   - type: 问题类型
   - duration_minutes: 预计用时
   - evaluation_points: 考察点列表
   - reference_answer: 参考答案要点
   - follow_up_questions: 可能的追问列表

建议的环节包括但不限于：
- 算法基础考察
- 项目经验深挖
- 系统设计能力
- 代码能力测试
- AI前沿理解
- 团队协作能力

请以JSON格式返回，确保格式正确。"""

        messages = [
            Message(
                role="system",
                content="你是一位经验丰富的技术面试官，擅长设计全面而有深度的面试题目。"
            ),
            Message(role="user", content=prompt)
        ]
        
        try:
            self.logger.info("调用LLM生成面试环节")
            response = self.llm.chat_completion(messages, temperature=0.7, max_tokens=3000)
            
            # 处理响应，尝试提取JSON
            content = response.content
            
            # 清理可能的markdown代码块标记
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
                
            self.logger.info(f"LLM返回内容长度: {len(content)}")
            
            try:
                sections = json.loads(content)
                self.logger.info(f"成功解析JSON，类型: {type(sections)}")
                
                # 确保sections是列表
                if not isinstance(sections, list):
                    if isinstance(sections, dict) and "sections" in sections:
                        sections = sections["sections"]
                    else:
                        sections = [sections]
                        
                # 验证sections的每个元素
                valid_sections = []
                for i, section in enumerate(sections):
                    if not isinstance(section, dict):
                        self.logger.warning(f"跳过无效的section: {section}")
                        continue
                        
                    # 确保必要字段存在
                    if "name" not in section:
                        section["name"] = f"面试环节{i+1}"
                    if "description" not in section:
                        section["description"] = "考察候选人的技能和经验"
                    if "duration_minutes" not in section:
                        section["duration_minutes"] = 15
                    if "questions" not in section or not isinstance(section["questions"], list):
                        section["questions"] = [{"question": "请介绍一下你的经验", "type": "开放问题", "duration_minutes": 5}]
                        
                    valid_sections.append(section)
                    
                self.logger.info(f"生成了{len(valid_sections)}个有效面试环节")
                return valid_sections[:max_sections]
                
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON解析失败: {e}")
                self.logger.debug(f"JSON内容: {content[:100]}...")
                # 使用默认环节
                return self._generate_default_sections()
        except Exception as e:
            self.logger.error(f"生成面试环节失败: {e}")
            return self._generate_default_sections()
    
    def _generate_default_sections(self, resume=None, jd=None) -> List[Dict[str, Any]]:
        """生成默认面试环节"""
        self.logger.info("使用默认面试环节")
        sections = []
        
        # 算法基础
        sections.append({
            "name": "算法模型基础原理",
            "description": "考察候选人的算法理论基础和对经典模型的理解",
            "duration_minutes": 20,
            "questions": [
                {
                    "question": "请解释一下Transformer的自注意力机制原理",
                    "type": "理论问题",
                    "duration_minutes": 10,
                    "evaluation_points": ["Transformer理解", "注意力机制", "表达能力"],
                    "reference_answer": "Query、Key、Value的计算过程，缩放点积注意力，多头注意力的作用",
                    "follow_up_questions": [
                        "为什么要进行缩放？",
                        "位置编码的作用是什么？",
                        "与RNN相比有什么优势？"
                    ]
                }
            ]
        })
        
        # 项目经验
        sections.append({
            "name": "项目工程实践经验",
            "description": "深入了解候选人的实际项目经验和问题解决能力",
            "duration_minutes": 25,
            "questions": [
                {
                    "question": "请详细介绍一个你最有成就感的AI项目",
                    "type": "经验问题",
                    "duration_minutes": 15,
                    "evaluation_points": ["项目复杂度", "技术深度", "问题解决能力", "成果影响"],
                    "reference_answer": "项目背景、技术挑战、解决方案、实施过程、最终效果",
                    "follow_up_questions": [
                        "遇到的最大技术挑战是什么？",
                        "如何评估模型效果？",
                        "有什么可以改进的地方？"
                    ]
                }
            ]
        })
        
        return sections
    
    async def _generate_closing(self) -> Dict[str, Any]:
        """生成结束环节"""
        return {
            "duration_minutes": 5,
            "steps": [
                "询问候选人是否还有其他想要补充的内容",
                "给候选人提问的机会：你有什么想要了解的吗？",
                "回答候选人关于公司、团队、项目的问题",
                "告知后续流程：感谢你今天的时间，后续如果有进一步的消息，HR会及时与你联系",
                "友好道别"
            ]
        } 
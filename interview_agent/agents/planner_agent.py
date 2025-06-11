"""
PlannerAgent - 规划面试流程
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json

from ..core.base_agent import BaseAgent, AgentContext, MessageType
from ..core.llm_client import WildcardLLMClient, Message
from config.settings import settings


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
        self.llm = WildcardLLMClient(
            api_key=settings.wildcard_api_key,
            api_base=settings.wildcard_api_base,
            model=settings.llm_model,
            temperature=settings.planner_temperature,
            max_tokens=settings.planner_max_tokens
        )
        self.default_sections = [
            "算法模型基础原理",
            "项目工程实践经验", 
            "AI前沿开放性问题",
            "候选人提问环节"
        ]
        # 从settings中获取简历截断长度
        self.resume_max_length = int(settings.resume_max_length if hasattr(settings, 'resume_max_length') else 2000)
    
    async def process(self, context: AgentContext) -> AgentContext:
        """处理规划任务"""
        try:
            # 保存context供其他方法使用
            self.context = context
            
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
        
        # 获取岗位类型
        position_type = "通用"
        position = "职位未知"
        if hasattr(self, 'context') and self.context:
            position_type = self.context.get_variable("position_type", "通用")
            
            # 获取具体职位名称
            jd_text = self.context.get_variable("jd_text", "")
            if "岗位" in jd_text and "：" in jd_text:
                try:
                    position = jd_text.split("岗位")[1].split("：")[1].split("\n")[0].strip()
                except:
                    pass
            
            if not position or position == "职位未知":
                # 根据岗位类型设置通用职位名称
                if position_type == "技术":
                    position = "工程师"
                elif position_type == "产品":
                    position = "产品经理"
                elif position_type == "设计":
                    position = "设计师"
                elif position_type == "销售":
                    position = "销售专员"
                elif position_type == "人力资源":
                    position = "HR专员"
                elif position_type == "财务":
                    position = "财务专员"
                else:
                    position = "专业人员"
        
        # 确保resume是字典
        if resume is None:
            self.logger.error("简历数据为空")
            return {
                "name": "候选人",
                "position": position,
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
            "position": position,
            "experience_years": f"{experience_years}年",
            "core_skills": core_skills
        }
    
    async def _generate_warmup(self, candidate_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成开场环节"""
        name = candidate_info.get("name", "候选人")
        
        # 获取岗位类型
        position_type = "通用"
        if hasattr(self, 'context') and self.context:
            position_type = self.context.get_variable("position_type", "通用")
        
        # 根据岗位类型定制面试环节描述
        interview_description = "技术问题讨论"
        if position_type == "技术":
            interview_description = "技术问题讨论"
        elif position_type == "产品":
            interview_description = "产品设计讨论"
        elif position_type == "设计":
            interview_description = "设计方案讨论"
        elif position_type == "销售":
            interview_description = "销售场景模拟"
        elif position_type == "人力资源":
            interview_description = "HR专业问题"
        elif position_type == "财务":
            interview_description = "财务分析讨论"
        
        return {
            "duration_minutes": 5,
            "steps": [
                f"面试官自我介绍：你好{name}，我是今天的面试官，负责{position_type}面试环节",
                "候选人回应：你好面试官",
                f"介绍面试流程：今天的面试大概分为以下几个环节：1）自我介绍 2）{interview_description} 3）项目经验交流 4）开放性问题 5）你的提问时间",
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
        
        # 获取岗位类型
        position_type = "通用"
        if hasattr(self, 'context') and self.context:
            position_type = self.context.get_variable("position_type", "通用")
        self.logger.info(f"使用岗位类型: {position_type}")
        
        # 根据岗位类型定制系统提示词
        system_prompt = "你是一位经验丰富的面试官，擅长设计全面而有深度的面试题目。"
        if position_type == "技术":
            system_prompt = "你是一位经验丰富的技术面试官，擅长设计考察编程、算法、系统设计等技术能力的面试题目。"
        elif position_type == "产品":
            system_prompt = "你是一位经验丰富的产品面试官，擅长设计考察产品思维、用户需求分析、市场洞察等能力的面试题目。"
        elif position_type == "设计":
            system_prompt = "你是一位经验丰富的设计面试官，擅长设计考察视觉设计、交互设计、用户体验等能力的面试题目。"
        elif position_type == "销售":
            system_prompt = "你是一位经验丰富的销售面试官，擅长设计考察销售技巧、客户沟通、谈判能力等方面的面试题目。"
        elif position_type == "人力资源":
            system_prompt = "你是一位经验丰富的HR面试官，擅长设计考察人才管理、组织发展、员工关系等方面的面试题目。"
        elif position_type == "财务":
            system_prompt = "你是一位经验丰富的财务面试官，擅长设计考察财务分析、预算管理、财务规划等能力的面试题目。"
            
        # 安全处理resume
        if not isinstance(resume, dict):
            self.logger.warning(f"resume不是字典类型: {type(resume)}")
            resume = {}
            
        # 限制resume大小，避免token超限
        resume_json = json.dumps(resume, ensure_ascii=False)
        if len(resume_json) > self.resume_max_length:
            self.logger.info(f"resume过大，进行截断(限制{self.resume_max_length}字符)")
            resume_json = resume_json[:self.resume_max_length] + "..."
        
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
   - question: 问题内容（必须具体明确，针对候选人的经历和应聘岗位）
   - type: 问题类型
   - duration_minutes: 预计用时
   - evaluation_points: 考察点列表（至少3个考察点）
   - reference_answer: 参考答案要点（提供详细的评分要点）
   - follow_up_questions: 可能的追问列表（至少2-3个追问）

重要提示：
1. 必须根据候选人简历中提到的具体技能和项目经验设计针对性问题
2. 问题应当从基础到进阶，逐步深入，确保每个问题都能考察候选人的真实能力
3. 每个环节至少包含3个具体问题，确保问题详细且有深度
4. 每个问题必须包含明确的考察点和可能的追问，以便面试官进行深入提问
5. 为每个问题提供参考答案要点，帮助面试官评估候选人回答质量
6. 结合候选人简历中提到的具体项目经验设计问题

建议的环节类型（根据岗位要求选择适合的环节）：
- 专业知识考察：根据岗位核心技能设计相关问题
- 项目经验深挖：详细了解项目中使用的技术、遇到的挑战及解决方案
- 技术细节探讨：针对候选人熟悉的技术栈进行深入提问
- 实际问题解决：设计与岗位相关的实际问题，考察解决方案
- 行业前沿理解：了解对行业前沿技术的理解和见解
- 团队协作能力：了解在项目中的协作经历和沟通能力

请以JSON格式返回，确保格式正确。"""

        messages = [
            Message(
                role="system",
                content=system_prompt
            ),
            Message(role="user", content=prompt)
        ]
        
        try:
            self.logger.info("调用LLM生成面试环节")
            response = self.llm.chat_completion(messages)
            
            # 处理响应，尝试提取JSON
            content = response.content
            
            # 打印完整的LLM响应内容，便于调试
            self.logger.info("LLM完整响应内容：")
            self.logger.info(content)
            
            # 清理可能的markdown代码块标记
            if '```json' in content:
                self.logger.info("检测到JSON代码块标记，进行清理")
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                self.logger.info("检测到代码块标记，进行清理")
                content = content.split('```')[1].split('```')[0]
                
            self.logger.info(f"LLM返回内容长度: {len(content)}")
            
            try:
                try:
                    # 尝试解析JSON
                    sections = json.loads(content)
                    self.logger.info(f"成功解析JSON，类型: {type(sections)}")
                    
                    # 检查是否有嵌套的sections字段
                    if isinstance(sections, dict):
                        if "sections" in sections and isinstance(sections["sections"], list):
                            sections = sections["sections"]
                            self.logger.info("从字典中提取sections列表字段")
                        # 检查是否有单个section对象
                        elif any(key in sections for key in ["name", "description", "questions"]):
                            self.logger.info("检测到单个section对象，转换为列表")
                            sections = [sections]
                        else:
                            # 尝试找到第一个是列表的字段
                            list_fields = [k for k, v in sections.items() if isinstance(v, list)]
                            if list_fields:
                                sections = sections[list_fields[0]]
                                self.logger.info(f"从字典中提取第一个列表字段: {list_fields[0]}")
                            else:
                                self.logger.info("将整个字典作为一个section包装为列表")
                                sections = [sections]
                    # 确保sections是列表
                    if not isinstance(sections, list):
                        self.logger.info(f"返回的不是列表，类型是: {type(sections)}")
                        sections = [sections]
                        self.logger.info("将非列表对象包装为列表")
                except json.JSONDecodeError as json_err:
                    # 获取错误位置
                    error_pos = json_err.pos
                    error_line = json_err.lineno
                    error_col = json_err.colno
                    
                    # 打印错误位置前后的内容
                    start_pos = max(0, error_pos - 200)
                    end_pos = min(len(content), error_pos + 200)
                    context_before = content[start_pos:error_pos]
                    context_after = content[error_pos:end_pos]
                    
                    self.logger.error(f"JSON解析失败: {str(json_err)}")
                    self.logger.error(f"错误位置: 行 {error_line}, 列 {error_col}, 字符位置 {error_pos}")
                    self.logger.error(f"错误位置前的内容: \n{context_before}")
                    self.logger.error(f"错误位置后的内容: \n{context_after}")
                    
                    # 查找可能的未转义引号
                    if '"' in context_before[-50:] or '"' in context_after[:50]:
                        self.logger.error("检测到可能的未转义引号，这可能是导致解析失败的原因")
                    
                    # 尝试自动修复常见问题
                    self.logger.info("尝试修复JSON格式...")
                    # 1. 尝试替换未转义的引号
                    fixed_content = content.replace('\\"', '__ESCAPED_QUOTE__')
                    fixed_content = fixed_content.replace('"', '\\"')
                    fixed_content = fixed_content.replace('__ESCAPED_QUOTE__', '\\"')
                    
                    # 2. 尝试处理多行文本
                    fixed_content = fixed_content.replace('\n', '\\n')
                    
                    # 重新包装成有效的JSON
                    fixed_content = f'[{fixed_content}]'
                    
                    try:
                        sections = json.loads(fixed_content)
                        self.logger.info("JSON自动修复成功!")
                    except:
                        # 如果修复失败，则使用默认环节
                        self.logger.error("JSON自动修复失败，使用默认环节")
                        return self._generate_default_sections()
                
                # 验证sections的每个元素
                valid_sections = []
                for i, section in enumerate(sections):
                    if not isinstance(section, dict):
                        self.logger.warning(f"跳过无效的section类型: {type(section)}")
                        continue
                        
                    # 确保必要字段存在
                    if "name" not in section or not section["name"]:
                        self.logger.warning(f"section {i} 缺少name字段，使用默认值")
                        section["name"] = f"面试环节{i+1}"
                        
                    if "description" not in section or not section["description"]:
                        self.logger.warning(f"section {i} 缺少description字段，使用默认值")
                        section["description"] = "考察候选人的技能和经验"
                        
                    if "duration_minutes" not in section or not isinstance(section["duration_minutes"], (int, float)):
                        self.logger.warning(f"section {i} 缺少有效的duration_minutes字段，使用默认值")
                        section["duration_minutes"] = 15
                        
                    # 处理问题列表
                    if "questions" not in section or not isinstance(section["questions"], list) or not section["questions"]:
                        self.logger.warning(f"section {i} 缺少有效的questions字段，使用默认值")
                        section["questions"] = [
                            {
                                "question": f"请介绍一下你在{section['name']}方面的经验",
                                "type": "开放问题",
                                "duration_minutes": 5,
                                "evaluation_points": ["专业知识", "表达能力", "实际经验"],
                                "reference_answer": "候选人应展示对相关领域的理解和实践经验",
                                "follow_up_questions": ["你在这方面的优势是什么?", "你如何解决过相关挑战?"]
                            }
                        ]
                    else:
                        # 验证每个问题的格式
                        for j, question in enumerate(section["questions"]):
                            if not isinstance(question, dict):
                                section["questions"][j] = {
                                    "question": f"问题{j+1}",
                                    "type": "开放问题",
                                    "duration_minutes": 5
                                }
                                continue
                                
                            if "question" not in question or not question["question"]:
                                question["question"] = f"{section['name']}相关问题{j+1}"
                                
                            if "type" not in question or not question["type"]:
                                question["type"] = "技术问题"
                                
                            if "duration_minutes" not in question or not isinstance(question["duration_minutes"], (int, float)):
                                question["duration_minutes"] = 5
                                
                            if "evaluation_points" not in question or not isinstance(question["evaluation_points"], list):
                                question["evaluation_points"] = ["专业知识", "解决问题能力", "表达能力"]
                                
                            if "reference_answer" not in question or not question["reference_answer"]:
                                question["reference_answer"] = "候选人应展示对相关领域的理解和实践经验"
                                
                            if "follow_up_questions" not in question or not isinstance(question["follow_up_questions"], list):
                                question["follow_up_questions"] = ["请详细说明", "你能举例说明吗?"]
                        
                    valid_sections.append(section)
                    
                self.logger.info(f"生成了{len(valid_sections)}个有效面试环节")
                return valid_sections[:max_sections]
                
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON解析失败: {e}")
                # 打印部分内容用于调试
                content_preview = content[:100] + "..." if len(content) > 100 else content
                self.logger.error(f"JSON内容预览: {content_preview}")
                # 将完整内容保存到文件
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_file = f"json_debug_{timestamp}.txt"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.logger.info(f"已保存完整JSON内容到文件: {debug_file}")
                # 使用默认环节
                return self._generate_default_sections()
        except Exception as e:
            import traceback
            self.logger.error(f"生成面试环节失败: {e}")
            self.logger.error(traceback.format_exc())
            return self._generate_default_sections()
    
    def _generate_default_sections(self, resume=None, jd=None) -> List[Dict[str, Any]]:
        """生成默认面试环节"""
        self.logger.info("使用默认面试环节")
        sections = []
        
        # 专业知识
        sections.append({
            "name": "专业知识考察",
            "description": "考察候选人的专业基础知识和理论理解",
            "duration_minutes": 20,
            "questions": [
                {
                    "question": "请介绍一下你在简历中提到的最熟悉的一项核心技能",
                    "type": "基础问题",
                    "duration_minutes": 5,
                    "evaluation_points": ["专业知识深度", "表达能力", "实际应用理解"],
                    "reference_answer": "候选人应展示对该技能的深入理解，包括基本原理、应用场景和实践经验",
                    "follow_up_questions": [
                        "这项技能在实际工作中如何应用？",
                        "与其他相关技术相比有什么优势？",
                        "你是如何学习和掌握这项技能的？"
                    ]
                },
                {
                    "question": "你认为这个岗位最需要哪些专业知识和技能？",
                    "type": "开放问题",
                    "duration_minutes": 5,
                    "evaluation_points": ["岗位理解", "专业判断", "自我认知"],
                    "reference_answer": "候选人应展示对岗位要求的准确理解，并结合自身经验阐述关键技能的重要性",
                    "follow_up_questions": [
                        "你在这些方面的优势是什么？",
                        "有哪些方面你认为还需要提升？",
                        "你如何保持这些专业知识的更新？"
                    ]
                }
            ]
        })
        
        # 项目经验
        sections.append({
            "name": "项目经验深挖",
            "description": "深入了解候选人的实际项目经验和问题解决能力",
            "duration_minutes": 25,
            "questions": [
                {
                    "question": "请详细介绍一个你最有成就感的项目",
                    "type": "经验问题",
                    "duration_minutes": 10,
                    "evaluation_points": ["项目复杂度", "技术深度", "问题解决能力", "成果影响"],
                    "reference_answer": "项目背景、技术选型、遇到的挑战、解决方案、实施过程、最终效果、个人贡献",
                    "follow_up_questions": [
                        "遇到的最大技术挑战是什么？",
                        "如何评估项目成果？",
                        "如果重新做这个项目，有什么可以改进的地方？"
                    ]
                },
                {
                    "question": "在团队项目中，你通常扮演什么角色？如何与团队成员协作？",
                    "type": "协作问题",
                    "duration_minutes": 5,
                    "evaluation_points": ["团队合作", "沟通能力", "角色定位"],
                    "reference_answer": "个人在团队中的职责、与不同角色的协作方式、沟通技巧、冲突处理",
                    "follow_up_questions": [
                        "如何处理团队意见分歧？",
                        "如何确保项目按时交付？",
                        "如何帮助团队成员提高效率？"
                    ]
                }
            ]
        })
        
        # 行业前沿
        sections.append({
            "name": "行业前沿与发展趋势",
            "description": "了解候选人对行业发展趋势的认知和见解",
            "duration_minutes": 15,
            "questions": [
                {
                    "question": "你如何看待行业的最新发展趋势？",
                    "type": "开放问题",
                    "duration_minutes": 5,
                    "evaluation_points": ["行业洞察", "前沿认知", "批判性思考"],
                    "reference_answer": "展示对行业最新动态的了解，分析未来可能的发展方向，结合实际应用场景",
                    "follow_up_questions": [
                        "这些趋势对你的工作有什么影响？",
                        "你认为存在哪些挑战和机遇？",
                        "你如何保持对行业前沿的关注？"
                    ]
                },
                {
                    "question": "你对未来1-2年内本行业技术发展有什么预测？",
                    "type": "前瞻问题",
                    "duration_minutes": 5,
                    "evaluation_points": ["前瞻思维", "技术视野", "实践洞察"],
                    "reference_answer": "基于当前技术发展状况，结合市场和应用需求，预测可能的技术演进方向",
                    "follow_up_questions": [
                        "你认为哪些技术会成为主流？",
                        "这些变化会带来哪些新的职业机会？",
                        "你如何适应这些变化？"
                    ]
                }
            ]
        })
        
        # 实际问题解决
        sections.append({
            "name": "实际问题解决能力",
            "description": "评估候选人面对实际问题的分析和解决能力",
            "duration_minutes": 20,
            "questions": [
                {
                    "question": "请描述一个你在工作中遇到的技术难题，以及你是如何解决的",
                    "type": "案例问题",
                    "duration_minutes": 10,
                    "evaluation_points": ["问题分析能力", "解决方案设计", "执行力", "技术应用"],
                    "reference_answer": "清晰描述问题背景、分析过程、解决思路、实施步骤和最终结果",
                    "follow_up_questions": [
                        "你考虑过哪些其他解决方案？",
                        "如何评估解决方案的有效性？",
                        "从中学到了什么经验教训？"
                    ]
                },
                {
                    "question": "如果给你一个新项目，你会如何规划和执行？",
                    "type": "方法论问题",
                    "duration_minutes": 5,
                    "evaluation_points": ["项目管理能力", "系统思考", "风险意识"],
                    "reference_answer": "项目评估、需求分析、技术选型、任务分解、时间规划、风险管理、质量控制",
                    "follow_up_questions": [
                        "如何处理项目中的未知风险？",
                        "如何平衡质量和进度的关系？",
                        "如何应对需求变更？"
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
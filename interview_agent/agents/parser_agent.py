"""
ParserAgent - 解析PDF文件并生成面试背景文档
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json

from ..core.base_agent import BaseAgent, AgentContext, MessageType
from ..core.resume_parser import ResumeParser
from ..core.llm_client import llm_client, Message


class ParserAgent(BaseAgent):
    """解析Agent - 处理简历PDF和JD，生成面试背景文档"""
    
    def __init__(self, name: str = "ParserAgent", **kwargs):
        super().__init__(name, description="解析简历和JD，生成面试背景文档", **kwargs)
        self.resume_parser = ResumeParser()
        self.llm = llm_client
    
    async def process(self, context: AgentContext) -> AgentContext:
        """处理解析任务"""
        try:
            # 获取输入参数
            pdf_files = context.get_variable("pdf_files", [])
            jd_text = context.get_variable("jd_text", "")
            extra_requirements = context.get_variable("extra_requirements", "")
            
            if not pdf_files:
                raise ValueError("没有提供PDF文件")
            
            self.add_message(context, "开始解析简历文件...", MessageType.SYSTEM)
            
            # 解析所有PDF文件
            all_resumes = []
            for pdf_file in pdf_files:
                self.logger.info(f"解析文件: {pdf_file}")
                parsed = self.resume_parser.parse(pdf_file)
                all_resumes.append(parsed)
            
            # 合并所有简历内容
            combined_resume = await self._combine_resumes(all_resumes)
            
            # 生成面试背景文档
            background_md = await self._generate_background_document(
                combined_resume,
                jd_text,
                extra_requirements
            )
            
            # 保存文档
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"interview_background_{timestamp}.md")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(background_md)
            
            # 更新上下文
            context.set_variable("background_document", background_md)
            context.set_variable("background_file", output_path)
            context.set_variable("parsed_resumes", all_resumes)
            context.set_variable("combined_resume", combined_resume)
            context.add_file("background", output_path)
            
            self.add_message(
                context, 
                f"面试背景文档已生成: {output_path}",
                MessageType.SYSTEM
            )
            
            return context
            
        except Exception as e:
            self.logger.error(f"解析失败: {e}")
            raise
    
    async def _combine_resumes(self, resumes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多份简历信息"""
        if len(resumes) == 1:
            return resumes[0]["structured_info"]
        
        # 使用LLM智能合并多份简历
        resumes_text = json.dumps([r["structured_info"] for r in resumes], ensure_ascii=False, indent=2)
        
        prompt = f"""请合并以下多份简历信息，生成一份完整的候选人档案。
如果存在冲突的信息，请选择最新或最完整的版本。

简历信息：
{resumes_text}

请返回合并后的JSON格式简历信息。"""

        messages = [
            Message(role="system", content="你是一个专业的简历分析助手。"),
            Message(role="user", content=prompt)
        ]
        
        response = self.llm.chat_completion(messages, temperature=0.1)
        
        try:
            return json.loads(response.content)
        except:
            # 如果解析失败，返回第一份简历
            return resumes[0]["structured_info"]
    
    async def _generate_background_document(self,
                                          resume: Dict[str, Any],
                                          jd: str,
                                          extra_requirements: str) -> str:
        """生成面试背景文档"""
        
        # 格式化简历信息
        resume_md = self._format_resume_to_markdown(resume)
        
        # 生成文档
        background = f"""# 面试背景信息

生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 一、候选人简历

{resume_md}

---

## 二、岗位要求（JD）

{jd if jd else "未提供具体岗位要求"}

---

## 三、额外面试要求

{extra_requirements if extra_requirements else "无额外要求"}

---

## 四、关键信息摘要

"""
        
        # 使用LLM生成关键信息摘要
        summary = await self._generate_summary(resume, jd, extra_requirements)
        background += summary
        
        return background
    
    def _format_resume_to_markdown(self, resume: Dict[str, Any]) -> str:
        """将简历信息格式化为Markdown"""
        md_lines = []
        
        # 基本信息
        if "basic_info" in resume:
            info = resume["basic_info"]
            md_lines.append("### 基本信息")
            md_lines.append(f"- **姓名**：{info.get('name', 'N/A')}")
            md_lines.append(f"- **邮箱**：{info.get('email', 'N/A')}")
            md_lines.append(f"- **电话**：{info.get('phone', 'N/A')}")
            md_lines.append(f"- **地址**：{info.get('location', 'N/A')}")
            if info.get('summary'):
                md_lines.append(f"\n**个人简介**：{info['summary']}")
            md_lines.append("")
        
        # 教育背景
        if "education" in resume and resume["education"]:
            md_lines.append("### 教育背景")
            for edu in resume["education"]:
                md_lines.append(f"- **{edu.get('school', 'N/A')}** - {edu.get('degree', '')} {edu.get('major', '')}")
                md_lines.append(f"  - 时间：{edu.get('start_date', '')} - {edu.get('end_date', '')}")
                if edu.get('gpa'):
                    md_lines.append(f"  - GPA：{edu['gpa']}")
            md_lines.append("")
        
        # 工作经历
        if "work_experience" in resume and resume["work_experience"]:
            md_lines.append("### 工作经历")
            for exp in resume["work_experience"]:
                md_lines.append(f"#### {exp.get('company', 'N/A')} - {exp.get('position', 'N/A')}")
                md_lines.append(f"*{exp.get('start_date', '')} - {exp.get('end_date', '')}*")
                if exp.get('description'):
                    md_lines.append(f"\n{exp['description']}")
                if exp.get('achievements'):
                    md_lines.append("\n**主要成就**：")
                    for achievement in exp['achievements']:
                        md_lines.append(f"- {achievement}")
                md_lines.append("")
        
        # 项目经历
        if "projects" in resume and resume["projects"]:
            md_lines.append("### 项目经历")
            for proj in resume["projects"]:
                md_lines.append(f"#### {proj.get('name', 'N/A')}")
                if proj.get('role'):
                    md_lines.append(f"**角色**：{proj['role']}")
                if proj.get('description'):
                    md_lines.append(f"\n{proj['description']}")
                if proj.get('technologies'):
                    md_lines.append(f"\n**技术栈**：{', '.join(proj['technologies'])}")
                if proj.get('achievements'):
                    md_lines.append("\n**成果**：")
                    for achievement in proj['achievements']:
                        md_lines.append(f"- {achievement}")
                md_lines.append("")
        
        # 技能
        if "skills" in resume:
            md_lines.append("### 技能")
            skills = resume["skills"]
            if skills.get('technical'):
                md_lines.append(f"- **技术技能**：{', '.join(skills['technical'])}")
            if skills.get('languages'):
                md_lines.append(f"- **编程语言**：{', '.join(skills['languages'])}")
            if skills.get('tools'):
                md_lines.append(f"- **工具**：{', '.join(skills['tools'])}")
            if skills.get('soft_skills'):
                md_lines.append(f"- **软技能**：{', '.join(skills['soft_skills'])}")
            md_lines.append("")
        
        return "\n".join(md_lines)
    
    async def _generate_summary(self, resume: Dict[str, Any], jd: str, extra_req: str) -> str:
        """生成关键信息摘要"""
        prompt = f"""基于候选人简历、岗位要求和额外面试要求，生成一份关键信息摘要。

候选人信息：
{json.dumps(resume, ensure_ascii=False, indent=2)}

岗位要求：
{jd}

额外要求：
{extra_req}

请生成包含以下内容的摘要：
1. 候选人与岗位的匹配度分析
2. 候选人的核心优势
3. 需要重点考察的领域
4. 建议的面试重点
5. 潜在的关注点或风险

请以清晰的Markdown格式输出。"""

        messages = [
            Message(role="system", content="你是一位经验丰富的招聘专家。"),
            Message(role="user", content=prompt)
        ]
        
        response = self.llm.chat_completion(messages, temperature=0.3)
        return response.content 
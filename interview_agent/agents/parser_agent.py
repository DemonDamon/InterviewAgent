"""
ParserAgent - 解析PDF文件并生成面试背景文档
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json
import traceback

from ..core.base_agent import BaseAgent, AgentContext, MessageType
from ..core.resume_parser import ResumeParser, LLMExtractor
from ..core.llm_client import WildcardLLMClient, Message
from config.settings import settings


class ParserAgent(BaseAgent):
    """解析Agent - 处理简历PDF和JD，生成面试背景文档"""
    
    def __init__(self, name: str = "ParserAgent", **kwargs):
        super().__init__(name, description="解析简历和JD，生成面试背景文档", **kwargs)
        self.llm = WildcardLLMClient(
            api_key=settings.wildcard_api_key,
            api_base=settings.wildcard_api_base,
            model=settings.llm_model,
            temperature=settings.parser_temperature,
            max_tokens=settings.parser_max_tokens
        )
        
        # 初始化LLMExtractor并传递LLM客户端
        llm_extractor = LLMExtractor(llm_client=self.llm)
        # 初始化ResumeParser，并使用我们的LLMExtractor
        self.resume_parser = ResumeParser()
        # 替换默认的extractor
        self.resume_parser.extractor = llm_extractor
    
    async def process(self, context: AgentContext) -> AgentContext:
        """处理解析任务"""
        try:
            # 保存context以供其他方法使用
            self.context = context
            
            # 获取输入参数
            pdf_files = context.get_variable("pdf_files", [])
            jd_text = context.get_variable("jd_text", "")
            extra_requirements = context.get_variable("extra_requirements", "")
            
            self.logger.info(f"获取输入参数 - PDF文件数量: {len(pdf_files)}, JD长度: {len(jd_text)}, 额外要求长度: {len(extra_requirements)}")
            
            if not pdf_files:
                self.logger.error("没有提供PDF文件")
                raise ValueError("没有提供PDF文件")
            
            self.add_message(context, "开始解析简历文件...", MessageType.SYSTEM)
            
            # 解析所有PDF文件
            all_resumes = []
            for i, pdf_file in enumerate(pdf_files):
                self.logger.info(f"开始解析第 {i+1}/{len(pdf_files)} 个文件: {pdf_file}")
                try:
                    parsed = self.resume_parser.parse(pdf_file)
                    self.logger.info(f"文件 {pdf_file} 解析成功，提取到 {len(parsed.get('structured_info', {}))} 个结构化信息")
                    all_resumes.append(parsed)
                except Exception as e:
                    self.logger.error(f"文件 {pdf_file} 解析失败: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    raise
            
            self.logger.info(f"所有PDF文件解析完成，共 {len(all_resumes)} 份简历")
            
            # 合并所有简历内容
            self.logger.info("开始合并简历信息...")
            combined_resume = await self._combine_resumes(all_resumes)
            self.logger.info(f"简历合并完成，合并后信息包含 {len(combined_resume)} 个字段")
            
            # 提取岗位类型
            self.logger.info("开始提取岗位类型...")
            position_type = await self._extract_position_type(jd_text)
            context.set_variable("position_type", position_type)
            self.logger.info(f"岗位类型提取完成: {position_type}")
            
            # 生成面试背景文档
            self.logger.info("开始生成面试背景文档...")
            background_md = await self._generate_background_document(
                combined_resume,
                jd_text,
                extra_requirements
            )
            self.logger.info(f"面试背景文档生成完成，长度: {len(background_md)}")
            
            # 保存文档
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"interview_background_{timestamp}.md")
            
            self.logger.info(f"正在保存面试背景文档到: {output_path}")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(background_md)
            
            # 更新上下文
            self.logger.info("正在更新上下文变量...")
            context.set_variable("background_document", background_md)
            context.set_variable("background_file", str(output_path))
            context.set_variable("parsed_resumes", all_resumes)
            context.set_variable("combined_resume", combined_resume)
            context.add_file("background", output_path)
            
            self.add_message(
                context, 
                f"面试背景文档已生成: {output_path}",
                MessageType.SYSTEM
            )
            
            self.logger.info("解析处理完成，成功返回")
            return context
            
        except Exception as e:
            self.logger.error(f"解析失败详细信息: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise
    
    async def _combine_resumes(self, resumes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多份简历信息"""
        self.logger.info(f"_combine_resumes: 开始合并 {len(resumes)} 份简历")
        
        if len(resumes) == 1:
            self.logger.info("只有一份简历，直接返回")
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
        
        self.logger.info("发送LLM请求合并简历...")
        try:
            response = self.llm.chat_completion(messages)
            self.logger.info(f"LLM合并简历请求成功，响应长度: {len(response.content)}")
            
            try:
                merged = json.loads(response.content)
                self.logger.info(f"合并简历解析成功，得到 {len(merged)} 个字段")
                return merged
            except Exception as e:
                self.logger.error(f"合并简历JSON解析失败: {str(e)}")
                self.logger.info("解析失败，返回第一份简历")
                return resumes[0]["structured_info"]
                
        except Exception as e:
            self.logger.error(f"LLM合并简历请求失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.logger.info("LLM请求失败，返回第一份简历")
            return resumes[0]["structured_info"]
    
    async def _generate_background_document(self,
                                          resume: Dict[str, Any],
                                          jd: str,
                                          extra_requirements: str) -> str:
        """生成面试背景文档"""
        self.logger.info("_generate_background_document: 开始生成面试背景文档")
        
        # 格式化简历信息
        self.logger.info("格式化简历为Markdown...")
        resume_md = self._format_resume_to_markdown(resume)
        self.logger.info(f"简历格式化完成，Markdown长度: {len(resume_md)}")
        
        # 生成文档
        self.logger.info("组装文档基本结构...")
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
        self.logger.info("开始生成关键信息摘要...")
        try:
            summary = await self._generate_summary(resume, jd, extra_requirements)
            self.logger.info(f"关键信息摘要生成成功，长度: {len(summary)}")
            background += summary
        except Exception as e:
            self.logger.error(f"生成关键信息摘要失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            background += "生成摘要时出错，请手动分析以上信息。"
        
        self.logger.info(f"面试背景文档生成完成，总长度: {len(background)}")
        return background
    
    def _format_resume_to_markdown(self, resume: Dict[str, Any]) -> str:
        """将简历信息格式化为Markdown"""
        self.logger.info("_format_resume_to_markdown: 开始格式化简历")
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
        
        formatted = "\n".join(md_lines)
        self.logger.info(f"简历格式化完成，共 {len(md_lines)} 行")
        return formatted
    
    async def _generate_summary(self, resume: Dict[str, Any], jd: str, extra_req: str) -> str:
        """生成关键信息摘要"""
        self.logger.info("_generate_summary: 开始生成摘要")
        
        # 转换resume为JSON并记录大小
        resume_json = json.dumps(resume, ensure_ascii=False, indent=2)
        self.logger.info(f"简历JSON长度: {len(resume_json)}字符")
        self.logger.info(f"JD长度: {len(jd)}字符")
        self.logger.info(f"额外要求长度: {len(extra_req)}字符")
        
        prompt = f"""基于候选人简历、岗位要求和额外面试要求，生成一份关键信息摘要。

候选人信息：
{resume_json}

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
        
        self.logger.info(f"开始请求LLM生成摘要，输入提示长度: {len(prompt)}")
        try:
            response = self.llm.chat_completion(messages)
            self.logger.info(f"LLM摘要生成成功，响应长度: {len(response.content)}")
            return response.content
        except Exception as e:
            self.logger.error(f"LLM摘要生成失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise
    
    async def _extract_position_type(self, jd: str) -> str:
        """从JD中提取岗位类型"""
        # 基于关键词的简单规则
        technical_keywords = ["程序", "开发", "工程师", "编程", "代码", "软件", "算法", "数据库", "架构", "后端", "前端", "全栈"]
        product_keywords = ["产品", "PM", "需求", "用户", "交互", "PRD", "原型", "用例"]
        design_keywords = ["设计", "UI", "UX", "用户体验", "视觉", "交互设计", "界面"]
        
        for keyword in technical_keywords:
            if keyword in jd:
                self.logger.info(f"通过关键词 '{keyword}' 匹配到岗位类型: 技术")
                return "技术"
                
        for keyword in product_keywords:
            if keyword in jd:
                self.logger.info(f"通过关键词 '{keyword}' 匹配到岗位类型: 产品")
                return "产品"
                
        for keyword in design_keywords:
            if keyword in jd:
                self.logger.info(f"通过关键词 '{keyword}' 匹配到岗位类型: 设计")
                return "设计"
        
        # 如果简单规则无法确定，使用LLM分析
        self.logger.info("关键词匹配失败，尝试使用LLM提取岗位类型")
        prompt = f"""根据以下岗位描述，判断该岗位属于哪种类型。
可能的类型包括：技术、产品、设计、市场、销售、人力资源、财务、管理、运营等。
只需回复一个词作为岗位类型。

岗位描述：
{jd[:500]}

岗位类型："""

        messages = [
            Message(role="system", content="你是一个岗位分析专家。"),
            Message(role="user", content=prompt)
        ]
        
        try:
            self.logger.info("开始LLM请求提取岗位类型")
            response = self.llm.chat_completion(messages)
            position_type = response.content.strip()
            self.logger.info(f"LLM提取岗位类型成功: {position_type}")
            return position_type
        except Exception as e:
            self.logger.error(f"LLM提取岗位类型失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.logger.info("返回默认岗位类型: 通用")
            return "通用" 
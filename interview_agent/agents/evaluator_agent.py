"""
EvaluatorAgent - 评估面试表现并生成报告
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import json
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import base64

from ..core.base_agent import BaseAgent, AgentContext, MessageType
from ..core.llm_client import WildcardLLMClient, Message
from config.settings import settings


class InterviewEvaluation:
    """面试评估结果"""
    def __init__(self):
        self.dimensions: Dict[str, float] = {}  # 评估维度和分数
        self.overall_score: float = 0.0
        self.strengths: List[str] = []
        self.weaknesses: List[str] = []
        self.recommendations: List[str] = []
        self.detailed_feedback: Dict[str, str] = {}
        self.hiring_recommendation: str = ""
    
    def add_dimension(self, name: str, score: float, feedback: str = ""):
        """添加评估维度"""
        self.dimensions[name] = score
        if feedback:
            self.detailed_feedback[name] = feedback
        self.calculate_overall_score()
    
    def calculate_overall_score(self):
        """计算总体得分"""
        if self.dimensions:
            self.overall_score = sum(self.dimensions.values()) / len(self.dimensions)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimensions": self.dimensions,
            "overall_score": self.overall_score,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
            "detailed_feedback": self.detailed_feedback,
            "hiring_recommendation": self.hiring_recommendation
        }


class EvaluatorAgent(BaseAgent):
    """评估Agent - 基于面试记录生成评估报告"""
    
    def __init__(self, name: str = "EvaluatorAgent", **kwargs):
        super().__init__(name, description="评估面试表现并生成报告", **kwargs)
        self.llm = WildcardLLMClient(
            api_key=settings.wildcard_api_key,
            api_base=settings.wildcard_api_base,
            model=settings.llm_model,
            temperature=settings.evaluator_temperature,
            max_tokens=settings.evaluator_max_tokens
        )
        
        # 设置中文字体
        self.setup_chinese_font()
    
    def setup_chinese_font(self):
        """设置中文字体"""
        try:
            # Windows系统
            self.font_path = "C:/Windows/Fonts/simhei.ttf"
            if not Path(self.font_path).exists():
                # macOS系统
                self.font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
                if not Path(self.font_path).exists():
                    # Linux系统
                    self.font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        except:
            self.font_path = None
    
    async def process(self, context: AgentContext) -> AgentContext:
        """处理评估任务"""
        try:
            # 获取输入
            conversation_history = context.get_variable("conversation_history", [])
            interview_plan = context.get_variable("interview_plan")
            jd_text = context.get_variable("jd_text")
            interview_record_file = context.get_variable("interview_record_file")
            
            if not conversation_history:
                raise ValueError("缺少面试对话记录")
            
            self.add_message(context, "开始评估面试表现...", MessageType.SYSTEM)
            
            # 生成评估
            evaluation = await self._evaluate_interview(
                conversation_history,
                interview_plan,
                jd_text
            )
            
            # 生成雷达图
            radar_image = self._generate_radar_chart(evaluation)
            
            # 生成评估报告海报
            poster_image = await self._generate_evaluation_poster(
                evaluation,
                radar_image,
                interview_plan
            )
            
            # 保存报告
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = Path(f"interview_evaluation_{timestamp}.png")
            poster_image.save(report_path)
            
            # 生成详细文字报告
            detailed_report = self._generate_detailed_report(evaluation, interview_plan)
            report_md_path = Path(f"interview_evaluation_{timestamp}.md")
            with open(report_md_path, 'w', encoding='utf-8') as f:
                f.write(detailed_report)
            
            # 更新上下文
            context.set_variable("evaluation", evaluation.to_dict())
            context.set_variable("evaluation_poster", str(report_path))
            context.set_variable("evaluation_report", str(report_md_path))
            context.add_file("evaluation_poster", report_path)
            context.add_file("evaluation_report", report_md_path)
            
            self.add_message(
                context,
                f"面试评估完成，总体得分：{evaluation.overall_score:.1f}/5.0",
                MessageType.SYSTEM
            )
            
            return context
            
        except Exception as e:
            self.logger.error(f"评估失败: {e}")
            raise
    
    async def _evaluate_interview(self,
                                conversation_history: List[Dict[str, Any]],
                                interview_plan: Dict[str, Any],
                                jd_text: str) -> InterviewEvaluation:
        """评估面试表现"""
        
        # 准备对话文本
        conversation_text = self._format_conversation(conversation_history)
        
        # 确定评估维度
        dimensions = await self._determine_evaluation_dimensions(jd_text, interview_plan)
        
        # 使用LLM进行评估
        evaluation_prompt = f"""请基于以下面试对话记录，评估候选人的表现。

【岗位要求】
{jd_text}

【面试对话】
{conversation_text[:8000]}  # 限制长度

【评估维度】
{json.dumps(dimensions, ensure_ascii=False)}

请对每个维度进行评分（1-5分），并提供详细的评估反馈。同时总结候选人的：
1. 主要优势（3-5点）
2. 主要不足（3-5点）
3. 改进建议（3-5点）
4. 录用建议（强烈推荐/推荐/保留/不推荐）

请以JSON格式返回评估结果。"""

        messages = [
            Message(
                role="system",
                content="你是一位经验丰富的技术面试评估专家，擅长全面、客观地评估候选人。"
            ),
            Message(role="user", content=evaluation_prompt)
        ]
        
        response = self.llm.chat_completion(messages)
        
        # 解析评估结果
        evaluation = InterviewEvaluation()
        try:
            eval_data = json.loads(response.content)
            
            # 设置各维度分数
            for dim, score in eval_data.get("dimensions", {}).items():
                feedback = eval_data.get("dimension_feedback", {}).get(dim, "")
                evaluation.add_dimension(dim, float(score), feedback)
            
            # 设置其他信息
            evaluation.strengths = eval_data.get("strengths", [])
            evaluation.weaknesses = eval_data.get("weaknesses", [])
            evaluation.recommendations = eval_data.get("recommendations", [])
            evaluation.hiring_recommendation = eval_data.get("hiring_recommendation", "保留")
            
        except Exception as e:
            self.logger.error(f"解析评估结果失败: {e}")
            # 使用默认评估
            for dim in dimensions:
                evaluation.add_dimension(dim, 3.0)
        
        return evaluation
    
    async def _determine_evaluation_dimensions(self, 
                                             jd_text: str,
                                             interview_plan: Dict[str, Any]) -> List[str]:
        """确定评估维度"""
        # 基础维度
        base_dimensions = [
            "技术能力",
            "项目经验",
            "问题解决",
            "沟通表达",
            "学习能力"
        ]
        
        # 从JD中提取额外维度
        if "算法" in jd_text:
            base_dimensions.append("算法功底")
        if "系统设计" in jd_text:
            base_dimensions.append("系统设计")
        if "团队" in jd_text or "协作" in jd_text:
            base_dimensions.append("团队协作")
        
        # 限制维度数量
        return base_dimensions[:6]
    
    def _format_conversation(self, conversation_history: List[Dict[str, Any]]) -> str:
        """格式化对话历史"""
        lines = []
        for turn in conversation_history:
            speaker = turn.get("speaker", "")
            content = turn.get("content", "")
            lines.append(f"{speaker}: {content}")
        return "\n".join(lines)
    
    def _generate_radar_chart(self, evaluation: InterviewEvaluation) -> Image.Image:
        """生成雷达图"""
        # 准备数据
        dimensions = list(evaluation.dimensions.keys())
        values = list(evaluation.dimensions.values())
        
        # 创建雷达图
        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(111, projection='polar')
        
        # 设置角度
        angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
        values += values[:1]  # 闭合图形
        angles += angles[:1]
        
        # 绘制雷达图
        ax.plot(angles, values, 'o-', linewidth=2, color='#1890ff')
        ax.fill(angles, values, alpha=0.25, color='#1890ff')
        
        # 设置标签
        ax.set_xticks(angles[:-1])
        if self.font_path:
            prop = fm.FontProperties(fname=self.font_path)
            ax.set_xticklabels(dimensions, fontproperties=prop, size=12)
        else:
            ax.set_xticklabels(dimensions, size=12)
        
        # 设置刻度
        ax.set_ylim(0, 5)
        ax.set_yticks([1, 2, 3, 4, 5])
        ax.set_yticklabels(['1', '2', '3', '4', '5'])
        
        # 添加网格
        ax.grid(True)
        
        # 保存为图片
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        radar_image = Image.open(buf)
        plt.close()
        
        return radar_image
    
    async def _generate_evaluation_poster(self,
                                        evaluation: InterviewEvaluation,
                                        radar_image: Image.Image,
                                        interview_plan: Dict[str, Any]) -> Image.Image:
        """生成评估报告海报"""
        # 创建海报画布
        poster_width = 1200
        poster_height = 1600
        poster = Image.new('RGB', (poster_width, poster_height), color='white')
        draw = ImageDraw.Draw(poster)
        
        # 加载字体
        try:
            if self.font_path:
                title_font = ImageFont.truetype(self.font_path, 48)
                header_font = ImageFont.truetype(self.font_path, 36)
                body_font = ImageFont.truetype(self.font_path, 24)
                small_font = ImageFont.truetype(self.font_path, 20)
            else:
                raise Exception("No font")
        except:
            # 使用默认字体
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # 绘制标题
        y_offset = 50
        title = "面试评估报告"
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((poster_width - title_width) // 2, y_offset), title, fill='black', font=title_font)
        
        # 候选人信息
        y_offset += 100
        candidate_info = interview_plan.get('candidate_info', {})
        info_text = f"候选人：{candidate_info.get('name', 'N/A')} | 岗位：{candidate_info.get('position', 'N/A')}"
        draw.text((100, y_offset), info_text, fill='#666666', font=body_font)
        
        # 总体评分
        y_offset += 60
        score_text = f"总体评分：{evaluation.overall_score:.1f} / 5.0"
        draw.text((100, y_offset), score_text, fill='#1890ff', font=header_font)
        
        # 录用建议
        y_offset += 50
        recommendation_color = {
            "强烈推荐": "#52c41a",
            "推荐": "#1890ff",
            "保留": "#faad14",
            "不推荐": "#f5222d"
        }.get(evaluation.hiring_recommendation, "#666666")
        
        draw.text((100, y_offset), f"录用建议：{evaluation.hiring_recommendation}", 
                 fill=recommendation_color, font=header_font)
        
        # 插入雷达图
        y_offset += 80
        radar_size = 500
        radar_resized = radar_image.resize((radar_size, radar_size), Image.Resampling.LANCZOS)
        radar_x = (poster_width - radar_size) // 2
        poster.paste(radar_resized, (radar_x, y_offset))
        
        # 优势
        y_offset += radar_size + 50
        draw.text((100, y_offset), "主要优势", fill='#52c41a', font=header_font)
        y_offset += 50
        for strength in evaluation.strengths[:3]:
            draw.text((120, y_offset), f"• {strength}", fill='black', font=body_font)
            y_offset += 35
        
        # 不足
        y_offset += 30
        draw.text((100, y_offset), "需要改进", fill='#faad14', font=header_font)
        y_offset += 50
        for weakness in evaluation.weaknesses[:3]:
            draw.text((120, y_offset), f"• {weakness}", fill='black', font=body_font)
            y_offset += 35
        
        # 建议
        y_offset += 30
        draw.text((100, y_offset), "发展建议", fill='#1890ff', font=header_font)
        y_offset += 50
        for recommendation in evaluation.recommendations[:3]:
            draw.text((120, y_offset), f"• {recommendation}", fill='black', font=body_font)
            y_offset += 35
        
        # 页脚
        footer_text = f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        draw.text((100, poster_height - 50), footer_text, fill='#999999', font=small_font)
        
        return poster
    
    def _generate_detailed_report(self, 
                                evaluation: InterviewEvaluation,
                                interview_plan: Dict[str, Any]) -> str:
        """生成详细文字报告"""
        report_lines = ["# 面试评估报告\n"]
        report_lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 基本信息
        candidate_info = interview_plan.get('candidate_info', {})
        report_lines.append("## 一、基本信息\n")
        report_lines.append(f"- **候选人**：{candidate_info.get('name', 'N/A')}")
        report_lines.append(f"- **应聘岗位**：{candidate_info.get('position', 'N/A')}")
        report_lines.append(f"- **面试时长**：{interview_plan.get('total_duration_minutes', 0)}分钟\n")
        
        # 总体评价
        report_lines.append("## 二、总体评价\n")
        report_lines.append(f"- **总体评分**：{evaluation.overall_score:.1f} / 5.0")
        report_lines.append(f"- **录用建议**：{evaluation.hiring_recommendation}\n")
        
        # 各维度评分
        report_lines.append("## 三、各维度评分\n")
        for dim, score in evaluation.dimensions.items():
            report_lines.append(f"### {dim}\n")
            report_lines.append(f"**评分**：{score:.1f} / 5.0\n")
            if dim in evaluation.detailed_feedback:
                report_lines.append(f"**详细反馈**：{evaluation.detailed_feedback[dim]}\n")
        
        # 主要优势
        report_lines.append("## 四、主要优势\n")
        for i, strength in enumerate(evaluation.strengths, 1):
            report_lines.append(f"{i}. {strength}")
        report_lines.append("")
        
        # 需要改进
        report_lines.append("## 五、需要改进的方面\n")
        for i, weakness in enumerate(evaluation.weaknesses, 1):
            report_lines.append(f"{i}. {weakness}")
        report_lines.append("")
        
        # 发展建议
        report_lines.append("## 六、发展建议\n")
        for i, recommendation in enumerate(evaluation.recommendations, 1):
            report_lines.append(f"{i}. {recommendation}")
        report_lines.append("")
        
        # 总结
        report_lines.append("## 七、总结\n")
        summary = self._generate_summary(evaluation)
        report_lines.append(summary)
        
        return "\n".join(report_lines)
    
    def _generate_summary(self, evaluation: InterviewEvaluation) -> str:
        """生成总结"""
        if evaluation.overall_score >= 4.5:
            level = "优秀"
        elif evaluation.overall_score >= 4.0:
            level = "良好"
        elif evaluation.overall_score >= 3.5:
            level = "合格"
        elif evaluation.overall_score >= 3.0:
            level = "基本合格"
        else:
            level = "不合格"
        
        summary = f"候选人整体表现{level}，综合得分{evaluation.overall_score:.1f}分。"
        
        if evaluation.hiring_recommendation in ["强烈推荐", "推荐"]:
            summary += "建议进入下一轮面试或发放offer。"
        elif evaluation.hiring_recommendation == "保留":
            summary += "建议暂时保留，可考虑与其他候选人比较后再做决定。"
        else:
            summary += "建议暂不考虑录用。"
        
        return summary 
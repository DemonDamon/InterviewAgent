"""
面试智能体Gradio应用
"""

import gradio as gr
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json
from datetime import datetime
import tempfile
import logging

# 导入Agent模块
from interview_agent.agents import (
    ParserAgent,
    PlannerAgent,
    ExecutorAgent,
    EvaluatorAgent
)
from interview_agent.core.base_agent import AgentContext
from interview_agent.agents.executor_agent import InterviewState

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 默认的JD模板
DEFAULT_JDS = {
    "初中级算法工程师": """
## 岗位职责
1. 负责机器学习/深度学习算法的研发和优化
2. 参与模型训练、调优和部署工作
3. 跟踪业界最新技术进展，推动技术创新

## 任职要求
1. 计算机、数学等相关专业本科及以上学历
2. 1-3年算法开发经验
3. 熟悉Python，掌握TensorFlow/PyTorch等深度学习框架
4. 熟悉常见的机器学习算法和深度学习模型
5. 具备良好的编程能力和工程实践经验
6. 良好的沟通能力和团队合作精神
""",
    
    "高级算法工程师": """
## 岗位职责
1. 负责核心算法架构设计和技术方案制定
2. 带领团队进行算法创新和工程落地
3. 解决复杂的技术难题，提升产品性能
4. 指导初级工程师，推动团队技术成长

## 任职要求
1. 计算机、数学等相关专业硕士及以上学历
2. 5年以上算法开发经验，有大规模项目落地经验
3. 精通机器学习/深度学习理论，熟悉前沿技术
4. 熟练掌握分布式训练、模型优化、部署等技术
5. 具备系统设计能力，能够设计高性能算法系统
6. 优秀的问题分析和解决能力
7. 良好的团队管理和沟通协调能力
"""
}

# 全局变量存储应用状态
class AppState:
    def __init__(self):
        self.context: Optional[AgentContext] = None
        self.executor_agent: Optional[ExecutorAgent] = None
        self.interview_task: Optional[asyncio.Task] = None
        self.is_interview_active = False
        
app_state = AppState()


async def process_files_and_plan(
    files: List[Any],
    jd_text: str,
    extra_requirements: str,
    progress=gr.Progress()
) -> Tuple[str, str, str]:
    """处理文件并生成面试计划"""
    try:
        progress(0, desc="开始处理...")
        
        # 初始化上下文
        context = AgentContext()
        
        # 保存上传的文件
        pdf_files = []
        if files:
            for file in files:
                if hasattr(file, 'name'):
                    pdf_files.append(Path(file.name))
        
        context.set_variable("pdf_files", pdf_files)
        context.set_variable("jd_text", jd_text)
        context.set_variable("extra_requirements", extra_requirements)
        
        # 1. 解析阶段
        progress(0.2, desc="解析简历文件...")
        parser = ParserAgent()
        context = await parser.run(context)
        background_doc = context.get_variable("background_document", "")
        
        # 2. 规划阶段
        progress(0.6, desc="规划面试流程...")
        planner = PlannerAgent()
        context = await planner.run(context)
        panel_doc = context.get_variable("interview_panel_md", "")
        
        # 保存到全局状态
        app_state.context = context
        
        progress(1.0, desc="完成！")
        
        return background_doc, panel_doc, "处理成功！面试流程已生成。"
        
    except Exception as e:
        logger.error(f"处理失败: {e}")
        return "", "", f"处理失败: {str(e)}"


async def start_interview(enable_voice: bool) -> Tuple[str, Dict]:
    """开始面试"""
    try:
        if not app_state.context:
            return "请先上传简历并生成面试计划", {}
        
        # 创建Executor
        app_state.executor_agent = ExecutorAgent(enable_voice=enable_voice)
        
        # 设置回调
        app_state.executor_agent.on_state_change = lambda state: logger.info(f"面试状态: {state}")
        
        # 启动面试任务
        app_state.is_interview_active = True
        app_state.interview_task = asyncio.create_task(
            app_state.executor_agent.run(app_state.context)
        )
        
        return "面试已开始", {"visible": True}
        
    except Exception as e:
        logger.error(f"启动面试失败: {e}")
        return f"启动失败: {str(e)}", {"visible": False}


async def send_supervisor_instruction(instruction: str) -> str:
    """发送监督员指令"""
    try:
        if app_state.executor_agent and app_state.is_interview_active:
            await app_state.executor_agent.add_supervisor_instruction(instruction)
            return f"指令已发送: {instruction}"
        else:
            return "面试未开始或已结束"
    except Exception as e:
        return f"发送失败: {str(e)}"


async def stop_interview() -> str:
    """停止面试"""
    try:
        if app_state.executor_agent:
            app_state.executor_agent.end_interview()
            app_state.is_interview_active = False
            
            if app_state.interview_task:
                app_state.interview_task.cancel()
            
            return "面试已停止"
        return "没有正在进行的面试"
    except Exception as e:
        return f"停止失败: {str(e)}"


async def generate_evaluation(progress=gr.Progress()) -> Tuple[str, str, str]:
    """生成面试评估报告"""
    try:
        if not app_state.context:
            return "", "", "请先完成面试"
        
        progress(0, desc="开始生成评估报告...")
        
        # 创建评估Agent
        evaluator = EvaluatorAgent()
        
        progress(0.5, desc="分析面试表现...")
        context = await evaluator.run(app_state.context)
        
        # 获取结果
        poster_path = context.get_variable("evaluation_poster", "")
        report_path = context.get_variable("evaluation_report", "")
        
        # 读取报告内容
        report_content = ""
        if report_path and Path(report_path).exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
        
        progress(1.0, desc="评估完成！")
        
        return str(poster_path), report_content, "评估报告已生成"
        
    except Exception as e:
        logger.error(f"生成评估失败: {e}")
        return "", "", f"生成失败: {str(e)}"


def create_interview_panel_ui():
    """创建面试面板UI"""
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 面试控制")
            enable_voice = gr.Checkbox(label="启用语音交互", value=False)
            start_btn = gr.Button("开始面试", variant="primary")
            stop_btn = gr.Button("结束面试", variant="stop")
            
            gr.Markdown("### 监督员控制")
            supervisor_input = gr.Textbox(
                label="监督员指令",
                placeholder="输入临时指令，如：请深入询问候选人的分布式训练经验",
                lines=2
            )
            send_instruction_btn = gr.Button("发送指令")
            
        with gr.Column(scale=3):
            gr.Markdown("### 面试进行中")
            # 这里可以添加音频波形组件
            audio_visualizer = gr.HTML("""
                <div style="height: 200px; background: linear-gradient(45deg, #667eea 0%, #764ba2 100%); 
                           border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                    <div style="color: white; font-size: 24px;">
                        🎤 语音交互界面（开发中）
                    </div>
                </div>
            """)
            
            conversation_display = gr.Chatbot(
                label="对话记录",
                height=400
            )
    
    return {
        "enable_voice": enable_voice,
        "start_btn": start_btn,
        "stop_btn": stop_btn,
        "supervisor_input": supervisor_input,
        "send_instruction_btn": send_instruction_btn,
        "audio_visualizer": audio_visualizer,
        "conversation_display": conversation_display
    }


# 创建Gradio界面
with gr.Blocks(
    title="AI面试智能体", 
    theme=gr.themes.Soft(),
    css=".scrollable-column { height: 70vh; overflow-y: auto; border: 1px solid #e0e0e0; padding: 10px; border-radius: 5px; }"
) as demo:
    gr.Markdown("""
    # 🤖 AI面试智能体系统
    
    欢迎使用AI面试智能体！本系统可以自动解析简历、规划面试流程、执行面试并生成评估报告。
    """)
    
    with gr.Tab("📄 简历上传与解析"):
        with gr.Row():
            with gr.Column(scale=1):
                file_upload = gr.File(
                    label="上传简历PDF",
                    file_count="multiple",
                    file_types=[".pdf"]
                )
                
                gr.Markdown("### 岗位JD")
                jd_preset = gr.Radio(
                    label="预设岗位",
                    choices=list(DEFAULT_JDS.keys()),
                    value="初中级算法工程师"
                )
                jd_input = gr.Textbox(
                    label="岗位描述",
                    lines=10,
                    value=DEFAULT_JDS["初中级算法工程师"]
                )
                
                extra_requirements = gr.Textbox(
                    label="额外面试要求",
                    placeholder="例如：重点考察候选人的创新能力和团队协作经验",
                    lines=3
                )
                
                process_btn = gr.Button("生成面试计划", variant="primary", size="lg")
            
            with gr.Column(scale=2):
                with gr.Tab("面试背景"):
                    with gr.Column(elem_classes=["scrollable-column"]):
                        background_display = gr.Markdown(label="面试背景文档")
                    copy_background_btn = gr.Button("复制背景信息")

                with gr.Tab("面试流程"):
                    with gr.Column(elem_classes=["scrollable-column"]):
                        panel_display = gr.Markdown(label="面试流程规划")
                    copy_panel_btn = gr.Button("复制流程规划")

                status_text = gr.Textbox(label="处理状态", interactive=False)
    
    with gr.Tab("🎙️ 面试执行"):
        interview_panel = create_interview_panel_ui()
        interview_status = gr.Textbox(label="面试状态", interactive=False)
    
    with gr.Tab("📊 评估报告"):
        generate_report_btn = gr.Button("生成评估报告", variant="primary", size="lg")
        
        with gr.Row():
            with gr.Column():
                report_image = gr.Image(label="评估报告海报", type="filepath")
                download_poster_btn = gr.Button("下载海报")
            
            with gr.Column():
                report_text = gr.Markdown(label="详细评估报告")
                download_report_btn = gr.Button("下载报告")
        
        eval_status = gr.Textbox(label="生成状态", interactive=False)
    
    # 事件绑定
    jd_preset.change(
        lambda x: DEFAULT_JDS.get(x, ""),
        inputs=[jd_preset],
        outputs=[jd_input]
    )
    
    process_btn.click(
        process_files_and_plan,
        inputs=[file_upload, jd_input, extra_requirements],
        outputs=[background_display, panel_display, status_text]
    )
    
    copy_background_btn.click(
        lambda x: x,
        inputs=[background_display],
        outputs=[gr.Textbox(visible=False)],  # Dummy output
        js="""
        (x) => {
            navigator.clipboard.writeText(x);
            alert("背景信息已复制到剪贴板");
        }
        """
    )

    copy_panel_btn.click(
        lambda x: x,
        inputs=[panel_display],
        outputs=[gr.Textbox(visible=False)], # Dummy output
        js="""
        (x) => {
            navigator.clipboard.writeText(x);
            alert("面试流程已复制到剪贴板");
        }
        """
    )
    
    interview_panel["start_btn"].click(
        start_interview,
        inputs=[interview_panel["enable_voice"]],
        outputs=[interview_status, interview_panel["audio_visualizer"]]
    )
    
    interview_panel["stop_btn"].click(
        stop_interview,
        outputs=[interview_status]
    )
    
    interview_panel["send_instruction_btn"].click(
        send_supervisor_instruction,
        inputs=[interview_panel["supervisor_input"]],
        outputs=[interview_status]
    )
    
    generate_report_btn.click(
        generate_evaluation,
        outputs=[report_image, report_text, eval_status]
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True
    ) 
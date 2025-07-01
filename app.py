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
        self.running_loop: Optional[asyncio.AbstractEventLoop] = None
        
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


async def start_interview(enable_voice: bool, use_realtime_voice: bool = False) -> Tuple[str, Dict]:
    """开始面试"""
    # 捕获并保存主事件循环
    if not app_state.running_loop:
        try:
            app_state.running_loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.error("无法获取正在运行的事件循环。")
            return "启动失败：内部事件循环错误", {"visible": False}

    try:
        if not app_state.context:
            return "请先上传简历并生成面试计划", {"visible": False}
        
        # 检查面试计划是否存在
        interview_plan = app_state.context.get_variable("interview_plan")
        if not interview_plan:
            return "面试计划不存在，请先生成或手动输入面试计划", {"visible": False}
            
        # 创建Executor
        app_state.executor_agent = ExecutorAgent(
            enable_voice=enable_voice,
            use_realtime_voice=use_realtime_voice
        )
        
        # 设置回调
        app_state.executor_agent.on_state_change = lambda state: logger.info(f"面试状态: {state}")
        
        # 根据模式选择不同的启动方式
        if use_realtime_voice:
            # 实时语音模式
            try:
                # 启动执行器，并传入包含面试计划的上下文
                await app_state.executor_agent.start(app_state.context)
                
                # 从执行器处理后的上下文中获取语音会话
                voice_session = app_state.context.get_variable("voice_session")
                if voice_session and voice_session.voice_adapter.is_running:
                    app_state.is_interview_active = True
                    mode_text = "实时语音面试"
                    return f"{mode_text}已启动成功", {"visible": True}
                else:
                    return "启动实时语音面试失败：未能成功创建语音会话", {"visible": False}
                    
            except Exception as e:
                logger.error(f"启动实时语音面试失败: {e}", exc_info=True)
                return f"启动失败: {str(e)}", {"visible": False}
        else:
            # 传统模式（文本或传统语音）
            app_state.is_interview_active = True
            app_state.interview_task = asyncio.create_task(
                app_state.executor_agent.run(app_state.context)
            )
            
            mode_text = "语音面试" if enable_voice else "文本面试"
            return f"{mode_text}已开始", {"visible": True}
        
    except Exception as e:
        logger.error(f"启动面试失败: {e}", exc_info=True)
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


def stop_interview() -> str:
    """停止面试（同步接口，避免UI阻塞）"""
    if not app_state.running_loop or not app_state.running_loop.is_running():
        logger.error("事件循环不可用，无法安全地停止面试。")
        # 尝试硬性重置状态作为后备方案
        app_state.is_interview_active = False
        if app_state.executor_agent:
            app_state.executor_agent.end_interview()
        return "错误：事件循环不可用，已尝试强制停止。"
    
    logger.info("发送面试停止指令到后台执行...")
    # 提交异步停止任务到主事件循环，但不等待它完成
    asyncio.run_coroutine_threadsafe(_stop_interview_async(), app_state.running_loop)
    
    # 立即更新UI状态，给用户即时反馈
    return "面试停止指令已发送，正在后台安全关闭..."


async def _stop_interview_async():
    """停止面试的实际异步逻辑"""
    try:
        logger.info("开始执行异步停止流程...")
        
        # 检查是否有实时语音会话
        if app_state.context:
            voice_session = app_state.context.get_variable("voice_session")
            if voice_session:
                try:
                    logger.info("检测到实时语音会话，正在调用非阻塞停止...")
                    # 调用非阻塞的stop_interview，它会立即返回
                    await voice_session.stop_interview()
                    logger.info("非阻塞停止指令已成功调用")
                except Exception as e:
                    logger.error(f"调用语音会话停止方法时失败: {e}", exc_info=True)
        
        # 结束面试执行器状态
        if app_state.executor_agent:
            app_state.executor_agent.end_interview()
            logger.info("面试执行器状态已更新为'ENDED'")
        
        app_state.is_interview_active = False
        
        # 取消可能在运行的传统面试任务
        if app_state.interview_task and not app_state.interview_task.done():
            logger.info("正在取消传统面试任务...")
            app_state.interview_task.cancel()
            try:
                await app_state.interview_task
            except asyncio.CancelledError:
                logger.info("传统面试任务已成功取消")
            
        logger.info("面试停止流程已在后台启动。")

    except Exception as e:
        logger.error(f"异步停止面试流程时发生严重错误: {e}", exc_info=True)


def load_interview_template() -> str:
    """加载面试流程模板"""
    template = """# 面试流程规划

生成时间：2024-01-01 10:00:00

## 一、候选人基本信息

- **姓名**：张三
- **应聘岗位**：算法工程师
- **经验年限**：3年
- **核心技能**：Python、机器学习、深度学习、TensorFlow

## 二、面试开场（Warm-up）

**预计时长**：5分钟

### 开场流程：
1. 面试官自我介绍：你好张三，我是今天的面试官，负责技术面试环节
1. 介绍面试流程：今天的面试大概分为以下几个环节：1）自我介绍 2）技术问题讨论 3）项目经验交流 4）开放性问题 5）你的提问时间
1. 请候选人做1-2分钟的自我介绍
1. 基于自我介绍，提出一个轻松的破冰问题

## 三、正式面试环节

**总时长**：40分钟

### 1. 算法基础考察
**时长**：15分钟
**描述**：考察候选人的算法理论基础和编程能力

**问题列表**：

#### 问题1.1：请介绍一下你最熟悉的机器学习算法
- **类型**：基础问题
- **预计时间**：5分钟
- **考察点**：算法理解、表达能力、实际应用
- **参考答案要点**：算法原理、适用场景、优缺点、实际应用经验
- **追问方向**：
  - 这个算法在什么场景下表现最好？
  - 与其他算法相比有什么优势？
  - 你在实际项目中是如何使用的？

#### 问题1.2：给定一个数组，找出其中的第K大元素
- **类型**：编程题
- **预计时间**：10分钟
- **考察点**：编程能力、算法思维、优化意识
- **参考答案要点**：快速选择算法、时间复杂度O(n)、空间复杂度O(1)
- **追问方向**：
  - 有哪些不同的解法？
  - 各种解法的时间复杂度是多少？
  - 如何处理特殊情况？

### 2. 项目经验深挖
**时长**：15分钟
**描述**：深入了解候选人的实际项目经验

**问题列表**：

#### 问题2.1：请详细介绍你最有成就感的一个项目
- **类型**：经验问题
- **预计时间**：10分钟
- **考察点**：项目复杂度、技术深度、问题解决能力
- **参考答案要点**：项目背景、技术选型、遇到的挑战、解决方案、成果
- **追问方向**：
  - 遇到的最大技术挑战是什么？
  - 如何评估项目成果？
  - 有什么可以改进的地方？

#### 问题2.2：在团队协作中，你是如何保证代码质量的？
- **类型**：工程实践
- **预计时间**：5分钟
- **考察点**：工程能力、团队协作、质量意识
- **参考答案要点**：代码规范、Code Review、单元测试、CI/CD
- **追问方向**：
  - 如何处理代码冲突？
  - 如何推动团队采用最佳实践？

### 3. 开放性问题
**时长**：10分钟
**描述**：了解候选人的技术视野和学习能力

**问题列表**：

#### 问题3.1：你如何看待AI技术的最新发展？
- **类型**：开放问题
- **预计时间**：5分钟
- **考察点**：技术视野、批判性思考、学习能力
- **参考答案要点**：对前沿技术的了解、个人见解、实际应用思考
- **追问方向**：
  - 哪些技术你认为最有前景？
  - 这些技术会带来什么影响？

## 四、面试结束

**预计时长**：5分钟

### 结束流程：
- 感谢候选人的时间，询问是否有任何问题想要了解
- 候选人提问（关于团队、项目、公司文化等）
- 回答候选人的问题
- 介绍后续流程和时间安排
- 感谢并送别候选人

## 五、面试总结

- **总时长**：50分钟
- **环节数**：3个
- **总问题数**：5个
"""
    return template


def get_conversation_history() -> List[List[str]]:
    """获取对话历史用于显示"""
    try:
        if app_state.executor_agent and hasattr(app_state.executor_agent, 'conversation_history'):
            # 转换为Gradio Chatbot格式
            history = []
            for turn in app_state.executor_agent.conversation_history:
                if turn.speaker == "候选人":
                    # 候选人的消息在左边
                    history.append([turn.content, None])
                else:
                    # 面试官的消息在右边
                    if history and history[-1][1] is None:
                        history[-1][1] = turn.content
                    else:
                        history.append([None, turn.content])
            return history
        
        # 检查实时语音会话
        if app_state.context:
            voice_session = app_state.context.get_variable("voice_session")
            if voice_session and hasattr(voice_session, 'get_conversation_history'):
                return voice_session.get_conversation_history()
        
        return []
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}")
        return []


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
            use_realtime_voice = gr.Checkbox(
                label="使用实时语音模式（豆包）", 
                value=False,
                info="启用后将使用豆包实时语音进行智能对话"
            )
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
        "use_realtime_voice": use_realtime_voice,
        "start_btn": start_btn,
        "stop_btn": stop_btn,
        "supervisor_input": supervisor_input,
        "send_instruction_btn": send_instruction_btn,
        "audio_visualizer": audio_visualizer,
        "conversation_display": conversation_display
    }


async def use_manual_interview_plan(
    manual_plan_text: str,
    progress=gr.Progress()
) -> Tuple[str, str, str]:
    """使用手动输入的面试计划"""
    try:
        if not manual_plan_text.strip():
            return "", "", "请输入面试流程规划"
        
        progress(0, desc="处理手动输入...")
        
        # 初始化或获取现有上下文
        if not app_state.context:
            app_state.context = AgentContext()
        
        # 解析手动输入的面试流程
        progress(0.3, desc="解析面试流程...")
        
        # 从Markdown文本中提取面试计划
        # 这里需要解析Markdown格式的面试流程
        planner = PlannerAgent()
        
        # 尝试从Markdown解析面试计划
        try:
            interview_plan = planner.parse_markdown_to_plan(manual_plan_text)
            app_state.context.set_variable("interview_plan", interview_plan)
            app_state.context.set_variable("interview_panel_md", manual_plan_text)
            
            # 如果没有背景文档，创建一个简单的
            if not app_state.context.get_variable("background_document"):
                background_doc = f"""# 面试背景信息

## 说明
此面试使用手动输入的面试流程规划。

## 面试计划概要
- 总时长：{interview_plan.get('total_duration_minutes', 30)}分钟
- 环节数：{len(interview_plan.get('sections', []))}个

---

*注：请确保已上传候选人简历以获得完整的面试体验。*
"""
                app_state.context.set_variable("background_document", background_doc)
            
            progress(1.0, desc="完成！")
            
            background = app_state.context.get_variable("background_document", "")
            return background, manual_plan_text, "手动输入的面试流程已加载成功！"
            
        except Exception as parse_error:
            logger.error(f"解析面试流程失败: {parse_error}")
            return "", "", f"解析失败：{str(parse_error)}"
        
    except Exception as e:
        logger.error(f"处理手动输入失败: {e}")
        return "", "", f"处理失败: {str(e)}"


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
                
                with gr.Tab("手动输入"):
                    gr.Markdown("""
                    ### 手动输入面试流程
                    
                    如果您已有面试流程规划，可以直接在下方粘贴或编辑，然后点击"使用手动输入"按钮。
                    """)
                    
                    with gr.Row():
                        use_manual_btn = gr.Button("使用手动输入", variant="primary")
                        load_template_btn = gr.Button("加载示例模板", variant="secondary")
                    
                    manual_panel_input = gr.Textbox(
                        label="面试流程规划（Markdown格式）",
                        placeholder="请粘贴或输入面试流程规划...",
                        lines=20,
                        max_lines=50
                    )
                    manual_status = gr.Textbox(label="状态", interactive=False, visible=False)
                
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
        inputs=[interview_panel["enable_voice"], interview_panel["use_realtime_voice"]],
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
    
    use_manual_btn.click(
        use_manual_interview_plan,
        inputs=[manual_panel_input],
        outputs=[background_display, panel_display, status_text]
    )
    
    load_template_btn.click(
        load_interview_template,
        outputs=[manual_panel_input]
    )
    
    generate_report_btn.click(
        generate_evaluation,
        outputs=[report_image, report_text, eval_status]
    )
    
    # 添加定时更新对话历史的功能
    def update_conversation_display():
        """更新对话显示"""
        try:
            # 检查是否有活跃的面试
            if not app_state.is_interview_active:
                return []
            
            # 首先检查是否有实时语音会话
            if app_state.context:
                voice_session = app_state.context.get_variable("voice_session")
                if voice_session and hasattr(voice_session, 'get_conversation_history'):
                    try:
                        history = voice_session.get_conversation_history()
                        return history
                    except Exception as e:
                        logger.error(f"获取实时语音对话历史失败: {e}")
            
            # 回退到常规执行器的对话历史
            if app_state.executor_agent and hasattr(app_state.executor_agent, 'conversation_history'):
                # 转换为Gradio Chatbot格式
                history = []
                for turn in app_state.executor_agent.conversation_history:
                    if turn.speaker == "候选人":
                        # 候选人的消息在左边
                        history.append([turn.content, None])
                    else:
                        # 面试官的消息在右边
                        if history and history[-1][1] is None:
                            history[-1][1] = turn.content
                        else:
                            history.append([None, turn.content])
                return history
            
            return []
        except Exception as e:
            logger.error(f"更新对话显示失败: {e}")
            return []
    
    # 每2秒更新一次对话历史（当面试进行中时）
    interview_timer = gr.Timer(2.0)
    interview_timer.tick(
        update_conversation_display,
        outputs=[interview_panel["conversation_display"]]
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True
    ) 
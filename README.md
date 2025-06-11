# 🤖 AI面试智能体系统

一个基于大语言模型的智能面试系统，能够自动解析简历、规划面试流程、执行面试并生成评估报告。

## ✨ 核心功能

### 1. 📄 智能简历解析
- 支持多种格式（PDF、Word、Markdown等）
- 自动提取关键信息
- 多份简历智能合并
- 生成结构化的面试背景文档

### 2. 📋 面试流程规划
- 基于JD和简历自动规划面试环节
- 生成详细的问题列表和参考答案
- 预估各环节时间
- 支持自定义面试要求

### 3. 🎙️ 面试执行
- 支持文本/语音交互（TTS/STT）
- 智能追问和动态调整
- 监督员实时干预功能
- 自动记录对话内容

### 4. 📊 评估报告生成
- 多维度能力评估（雷达图）
- 生成可视化评估海报
- 详细的文字报告
- 录用建议和发展建议

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Windows/macOS/Linux

### 安装步骤

1. 克隆项目
```bash
git clone https://github.com/your-repo/interview-agent.git
cd interview-agent
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的API密钥
```

4. 启动系统
```bash
python run.py
```

5. 访问系统
打开浏览器访问 http://localhost:7860

## 🏗️ 系统架构

### Agent架构（参考Dify/n8n设计）
```
BaseAgent（基类）
├── ParserAgent    # 简历解析
├── PlannerAgent   # 面试规划
├── ExecutorAgent  # 面试执行
└── EvaluatorAgent # 评估生成
```

### 核心模块
- **base_agent.py**: 通用Agent基类，支持工作流编排
- **audio_handler.py**: TTS/STT音频处理
- **llm_client.py**: 统一的LLM调用接口
- **resume_parser.py**: 文档解析器，支持多种格式提取

## 📸 系统截图

### 面试背景信息与摘要生成
![面试背景信息与摘要生成](/assets/screenshot_1.png)

### 面试流程规划生成
![面试流程规划生成](/assets/screenshot_2.png)


## 📖 使用指南

### 1. 上传简历
- 支持批量上传PDF文件
- 选择预设JD或自定义输入
- 添加额外的面试要求

### 2. 生成面试计划
- 系统自动解析简历并生成背景文档
- 基于JD规划面试流程
- 可查看和编辑生成的面试计划

### 3. 执行面试
- 选择是否启用语音交互
- 点击"开始面试"启动流程
- 监督员可随时发送指令调整面试方向

### 4. 查看评估报告
- 面试结束后生成综合评估
- 包含能力雷达图和详细分析
- 可下载报告和海报

## 🛠️ 高级配置

### 语音功能配置
```python
# 使用Edge TTS（默认）
audio_handler_type = "edge"

# 使用OpenAI兼容API
audio_handler_type = "openai"
api_key = "your-api-key"
```

### 自定义Agent
```python
from interview_agent.core.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    async def process(self, context):
        # 实现自定义逻辑
        pass
```

## 🔄 最近更新

- ✅ 增强了PlannerAgent的JSON解析能力，提升面试规划的稳定性
- ✅ 优化了简历解析模块的token限制配置，从硬编码改为可配置
- ✅ 添加了详细的错误处理和日志记录，便于调试
- ✅ 完善了数据验证逻辑，确保面试计划数据的完整性

## 📋 待办事项

- [ ] 完善语音交互界面
- [ ] 支持更多文档格式
- [ ] 添加面试录音功能
- [ ] 支持多语言
- [ ] 优化移动端体验
- [ ] 添加批量面试管理

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- 基于Gradio构建用户界面
- Agent架构参考了Dify和n8n的设计理念
- 使用Edge TTS提供语音合成功能

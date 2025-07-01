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
- Python 3.10+
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
- 上传PDF文件
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

## 🗣️ 实时语音模块单独运行指南

本系统包含一个独立的实时语音对话模块(`realtime_dialog`)，你可以单独运行它来进行测试。

### 1. 获取豆包实时语音API密钥

首先需要在火山引擎控制台获取豆包实时语音服务的API密钥：

1. 登录 [火山引擎控制台](https://console.volcengine.com/)
2. 进入"豆包端到端实时语音大模型"服务页面
    ![服务页面](/assets/火山引擎.png)
3. 在服务接入认证信息中：
   - **红色框内的 APP ID** 对应 `VOLC_APP_ID`
   - **绿色框内的 Access Token** 对应 `VOLC_ACCESS_KEY`
   - **蓝色框内的 Secret Key** 暂时可忽略

参考截图中的标识框获取对应的密钥信息。

### 2. 确认配置
确保你已经在根目录的 `.env` 文件中配置了以下参数：
```bash
# 豆包实时语音API配置
VOLC_APP_ID=你的APP_ID（红色框）
VOLC_ACCESS_KEY=你的ACCESS_KEY（绿色框） 
VOLC_APP_KEY=PlgvMymc7f3tQnJ6（官方文档称是固定值）
VOLC_RESOURCE_ID=volc.speech.dialog
```

### 3. 安装依赖
该模块有独立的依赖文件，从项目根目录执行以下命令：
```bash
pip install -r realtime_dialog/requirements.txt
```

### 4. 启动服务器
在项目根目录打开一个终端，运行以下命令来启动语音对话WebSocket服务器：
```bash
python realtime_dialog/main.py
```
服务器启动后会监听端口，等待客户端连接。

### 5. 启动客户端
在项目根目录**再打开一个新的终端**，运行以下命令来启动客户端：
```bash
python realtime_dialog/realtime_dialog_client.py
```
客户端会自动连接服务器。现在，你可以对着麦克风说话，程序会识别你的语音，并通过服务器返回AI的语音回答。

## 🔄 最近更新

- ✅ 增强了PlannerAgent的JSON解析能力，提升面试规划的稳定性
- ✅ 优化了简历解析模块的token限制配置，从硬编码改为可配置
- ✅ 添加了详细的错误处理和日志记录，便于调试
- ✅ 完善了数据验证逻辑，确保面试计划数据的完整性
- ✅ 增强了追问功能，现在能同时生成追问问题和参考答案要点
- ✅ 优化了面试背景信息展示，支持滚动和复制功能
- ✅ 集成了豆包实时语音对话模块，支持语音交互
- ✅ 改进了环境配置管理，提高了安全性和可维护性

## 📋 待办事项

- [ ] 完善语音交互界面的可视化效果
- [ ] 支持更多文档格式（Word、Excel等）
- [ ] 添加面试录音和回放功能
- [ ] 支持多语言界面（英文、日文等）
- [ ] 优化移动端体验和响应式设计
- [ ] 添加批量面试管理和调度功能
- [ ] 集成更多语音服务提供商（Azure、AWS等）
- [ ] 添加面试数据分析和统计功能
- [ ] 支持自定义评估标准和权重

## 🤝 贡献指南

欢迎提交Issue和Pull Request！在贡献之前，请：

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

MIT License

## 🙏 致谢

- 基于Gradio构建用户界面，提供了优秀的Web UI框架
- Agent架构参考了Dify和n8n的设计理念
- 使用Edge TTS和豆包实时语音提供语音合成和识别功能
- 感谢MinerU项目提供的文档解析能力
- 感谢所有贡献者和使用者的反馈和建议

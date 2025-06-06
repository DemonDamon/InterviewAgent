# InterviewAgent - 智能面试系统

InterviewAgent 是一个基于 AI 的智能面试系统，能够自动化进行技术面试，包括简历分析、定制化题目生成、实时对话交互和综合评估。

## 🌟 新特性

- **🔌 Wildcard API 支持**：通过统一的API接口访问多种大模型（Claude、GPT、Gemini）
- **🗄️ 向量数据库双支持**：同时支持 Milvus 和 Qdrant，灵活选择
- **🚀 快速开始脚本**：一键配置和运行系统
- **📝 基于职位描述的题目生成**：根据JD和面试官要求动态生成题目

## 🚀 核心功能

- **📄 智能简历解析**：自动提取候选人关键信息，生成候选人画像
- **🎯 定制化题目生成**：基于候选人背景、职位要求和面试官需求生成个性化面试题
- **💬 自然对话交互**：支持多轮对话、智能追问和引导
- **📊 全面评估体系**：多维度评估候选人的技术能力和软技能
- **📈 详细面试报告**：自动生成面试报告和改进建议
- **🌐 联网能力**：支持实时搜索和最新技术信息获取

## 🏗️ 系统架构

系统采用模块化设计，主要包含以下组件：

- **Resume Parser（简历解析器）**：解析多种格式的简历文件
- **Question Generator（题目生成器）**：基于LLM生成定制化面试题
- **Interview Conductor（面试执行器）**：管理面试流程和对话
- **LLM Client（统一LLM客户端）**：通过Wildcard API访问各种大模型
- **Vector Store（向量存储）**：支持Milvus和Qdrant的题库管理

### 系统架构图
```
graph TB
    subgraph "用户接口层"
        A[Web UI] --> B[API Gateway]
        C[CLI] --> B
    end
    
    subgraph "核心业务层"
        B --> D[面试执行器<br/>Interview Conductor]
        D --> E[题目生成器<br/>Question Generator]
        D --> F[简历解析器<br/>Resume Parser]
        D --> G[评估引擎<br/>Evaluation Engine]
    end
    
    subgraph "AI服务层"
        E --> H[Wildcard API<br/>Claude/GPT/Gemini]
        G --> H
        D --> H
    end
    
    subgraph "数据层"
        D --> I[(PostgreSQL<br/>面试记录)]
        E --> J[(Milvus/Qdrant<br/>题库/知识库)]
        D --> K[(Redis<br/>会话缓存)]
    end
    
    subgraph "文件存储"
        F --> L[简历文件<br/>MD/PDF/DOCX]
        G --> M[面试报告<br/>JSON/PDF]
    end
```

## 📦 快速开始

### 一键启动
```bash
python quickstart.py
```

这个脚本会：
1. 检查并创建环境配置
2. 验证依赖安装
3. 提供交互式菜单选择运行模式

### 手动安装

1. 克隆项目
```bash
git clone https://github.com/yourusername/InterviewAgent.git
cd InterviewAgent
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
```bash
# 运行配置助手
python example/config_example.py

# 或手动创建 .env 文件
# 编辑 .env 文件，填入您的 Wildcard API 密钥
```

## 🎮 使用方法

### 完整示例（推荐）

```bash
python example/run_interview_example.py
```

这会运行一个完整的面试流程示例，包括：
- 解析高柱亮的简历
- 生成算法工程师面试题
- 模拟面试对话
- 生成评估报告

### API 服务

```bash
python -m uvicorn api.main:app --reload
```

访问 http://localhost:8000/docs 查看 API 文档

### 代码示例

```python
from pathlib import Path
from interview_agent.core import (
    ResumeParser, 
    QuestionGenerator, 
    JobDescription,
    InterviewConductor
)

# 1. 解析简历
parser = ResumeParser()
profile = parser.parse(Path("data/candidate_resume.md"))

# 2. 定义职位要求
job_desc = JobDescription(
    title="算法工程师",
    requirements=["硕士学历", "3年经验", "熟悉深度学习"],
    responsibilities=["算法研发", "模型优化"]
)

# 3. 生成面试题
generator = QuestionGenerator()
questions = generator.generate_interview_plan(
    profile=profile,
    job_description=job_desc,
    interviewer_requirements="重点考察NLP和工程化能力",
    duration_minutes=45
)

# 4. 开始面试
conductor = InterviewConductor()
session = conductor.create_session(profile, questions)
conductor.start_interview(session.id)
```

## 🤖 支持的模型

通过 Wildcard API，系统支持以下模型：

### Claude 系列
- claude-3-5-sonnet-20241022（推荐）
- claude-opus-4-20250514
- claude-sonnet-4-20250514

### GPT 系列
- gpt-4-turbo
- gpt-4
- gpt-3.5-turbo

### Gemini 系列
- gemini-2.5-pro-preview-03-25
- gemini-2.5-flash-preview

在 `.env` 文件中修改 `LLM_MODEL` 配置即可切换模型。

## 📋 面试题目类型

- **算法题**：考察数据结构与算法基础
- **系统设计题**：评估架构设计能力
- **工程实践题**：了解实际项目经验
- **开放性问题**：探讨技术理解深度（如 RAG、AI Agent）
- **行为面试题**：评估软技能和团队协作能力

## 🔧 配置说明

主要配置项（在 `.env` 文件中设置）：

```bash
# Wildcard API 配置
WILDCARD_API_KEY=your-api-key
WILDCARD_API_BASE=https://api.gptsapi.net

# 模型配置
LLM_MODEL=claude-3-5-sonnet-20241022
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# 向量数据库配置
VECTOR_DB_TYPE=milvus  # 或 qdrant
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 面试配置
DEFAULT_INTERVIEW_DURATION=30
MAX_QUESTIONS_PER_INTERVIEW=10
```

## 🚧 开发计划

- [ ] 支持语音输入/输出
- [ ] 实时代码编辑器集成
- [ ] 多语言支持
- [ ] 面试回放功能
- [ ] 批量面试管理
- [ ] 与 ATS 系统集成
- [ ] 题库管理界面
- [ ] 面试官培训模式

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！请确保：

1. 代码符合 PEP 8 规范
2. 添加适当的测试
3. 更新相关文档

## 📄 许可证

MIT License

## 📧 联系方式

如有问题或建议，请通过以下方式联系：

- Issue: [GitHub Issues](https://github.com/yourusername/InterviewAgent/issues)
- Email: your-email@example.com

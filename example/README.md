# 面试智能体示例

本目录包含面试智能体的使用示例。

## 文件说明

- `run_interview_example.py` - 完整的面试流程示例，使用高柱亮的简历进行模拟面试
- `config_example.py` - 配置文件示例，展示如何设置环境变量

## 快速开始

### 1. 配置环境

首先，创建并配置 `.env` 文件：

```bash
cd example
python config_example.py  # 这会在项目根目录创建.env文件
```

编辑生成的 `.env` 文件，填入您的 Wildcard API 密钥。

### 2. 安装依赖

```bash
pip install -r ../requirements.txt
```

### 3. 运行示例

```bash
python run_interview_example.py
```

这个示例会：
1. 解析 `data/gaozhuliang.md` 简历
2. 根据算法工程师职位要求生成定制化面试题
3. 模拟面试对话过程
4. 生成面试评估报告

## 自定义使用

您可以修改 `run_interview_example.py` 中的以下部分：

### 修改职位要求
```python
job_description = JobDescription(
    title="您的职位名称",
    requirements=["要求1", "要求2"],
    responsibilities=["职责1", "职责2"]
)
```

### 修改面试官要求
```python
interviewer_requirements = """
您对候选人的特殊要求和重点考察方向
"""
```

### 使用其他简历
```python
resume_path = Path("../data/您的简历文件.md")
```

## 支持的模型

通过 Wildcard API，您可以使用以下模型：

- **Claude系列**: claude-3-5-sonnet-20241022, claude-opus-4-20250514
- **GPT系列**: gpt-4-turbo, gpt-4, gpt-3.5-turbo
- **Gemini系列**: gemini-2.5-pro-preview-03-25, gemini-2.5-flash-preview

在 `.env` 文件中修改 `LLM_MODEL` 即可切换模型。

## 注意事项

1. 确保 Wildcard API 密钥有效且有足够的额度
2. 首次运行可能需要较长时间生成题目
3. 如果遇到网络问题，系统会使用备用题目
4. 向量数据库（Milvus/Qdrant）是可选的，不影响基础功能 
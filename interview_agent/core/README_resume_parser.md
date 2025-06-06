# 简历解析器模块说明

## 概述

`resume_parser.py` 是一个通用的文档解析和信息抽取模块，支持多种文档格式（PDF、DOCX、Markdown、TXT），并使用大语言模型（LLM）进行智能信息抽取。

## 核心特性

1. **多格式支持**：自动识别并解析 PDF、DOCX、Markdown、TXT 等常见文档格式
2. **高级解析能力**：使用专业的解析库（pypdf、python-docx等）提取文档内容和元数据
3. **智能信息抽取**：利用 LLM 根据自定义模式从文档中抽取结构化信息
4. **业务逻辑解耦**：核心解析功能与具体业务需求完全分离，支持自定义抽取模式
5. **批量处理**：支持批量解析多个文档文件

## 架构设计

```
┌─────────────────┐
│  文档输入层     │
│ (PDF/DOCX/MD等) │
└────────┬────────┘
         │
┌────────▼────────┐
│ 文档解析层      │
│ DocumentParser  │
│ - PDFParser     │
│ - DocxParser    │
│ - MarkdownParser│
│ - TextParser    │
└────────┬────────┘
         │
┌────────▼────────┐
│ ParsedDocument  │
│ - raw_text      │
│ - metadata      │
│ - file_type     │
└────────┬────────┘
         │
┌────────▼────────┐
│ LLM抽取层       │
│ LLMExtractor    │
│ - 自定义schema  │
│ - 智能抽取      │
└────────┬────────┘
         │
┌────────▼────────┐
│ 结构化输出      │
│ JSON格式        │
└─────────────────┘
```

## 主要组件

### 1. DocumentParser（抽象基类）
定义文档解析器的标准接口：
- `can_parse()`: 检查是否可以解析特定文件
- `parse()`: 解析文档并返回 ParsedDocument

### 2. 具体解析器
- **PDFParser**: 使用 pypdf 解析 PDF 文件
- **DocxParser**: 使用 python-docx 解析 Word 文档
- **MarkdownParser**: 解析 Markdown 格式文档
- **TextParser**: 处理纯文本文件

### 3. UniversalDocumentParser
统一的文档解析入口，自动识别文件格式并调用相应的解析器。

### 4. LLMExtractor
基于大语言模型的信息抽取器，支持：
- 自定义抽取模式（schema）
- 额外的抽取指令
- 自动处理 JSON 格式化
- 降级处理机制

### 5. ResumeParser
高级 API，整合文档解析和信息抽取功能：
- 支持自定义抽取模式
- 提供默认的简历信息模式
- 支持批量处理

## 使用方式

### 基础使用
```python
from interview_agent.core.resume_parser import ResumeParser

# 使用默认模式解析简历
parser = ResumeParser()
result = parser.parse("resume.pdf")

# 获取结构化信息
basic_info = result['structured_info']['basic_info']
skills = result['structured_info']['skills']
```

### 自定义抽取模式
```python
# 定义自定义模式
custom_schema = {
    "specific_skills": {
        "frameworks": ["string"],
        "experience_years": "number"
    }
}

# 使用自定义模式
parser = ResumeParser(extraction_schema=custom_schema)
result = parser.parse("resume.pdf")
```

### 仅文档解析
```python
from interview_agent.core.resume_parser import UniversalDocumentParser

# 只进行文档解析，不使用LLM
doc_parser = UniversalDocumentParser()
parsed_doc = doc_parser.parse("document.pdf")
print(parsed_doc.raw_text)
```

## 扩展性

1. **添加新的文档格式**：继承 `DocumentParser` 基类并实现相应方法
2. **自定义抽取逻辑**：通过 schema 和 additional_instructions 参数定制
3. **集成其他 LLM**：修改 LLMExtractor 中的 LLM 调用逻辑

## 依赖项

- pypdf: PDF 文档解析
- python-docx: Word 文档解析
- markdown: Markdown 格式处理
- 项目内部的 llm_client 模块

## 注意事项

1. LLM 抽取可能产生 API 调用费用
2. 大文档会被截断以适应 LLM 的 token 限制
3. 复杂的表格或图表信息可能无法完全提取 
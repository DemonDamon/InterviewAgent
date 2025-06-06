"""
简历解析器使用示例

展示如何使用通用的简历解析器，支持自定义抽取模式
"""

from pathlib import Path
from interview_agent.core.resume_parser import ResumeParser


def example_basic_usage():
    """基础使用示例 - 使用默认的简历信息抽取模式"""
    print("=== 基础使用示例 ===\n")
    
    # 创建解析器实例
    parser = ResumeParser()
    
    # 解析简历文件
    resume_path = Path("example/sample_resume.pdf")  # 可以是PDF、DOCX、MD或TXT格式
    
    try:
        result = parser.parse(resume_path)
        
        print(f"文件类型: {result['file_type']}")
        print(f"文件元数据: {result['metadata']}")
        print("\n提取的结构化信息:")
        
        # 基础信息
        basic_info = result['structured_info'].get('basic_info', {})
        print(f"\n候选人姓名: {basic_info.get('name')}")
        print(f"邮箱: {basic_info.get('email')}")
        print(f"电话: {basic_info.get('phone')}")
        
        # 技能信息
        skills = result['structured_info'].get('skills', {})
        print(f"\n技术技能: {skills.get('technical', [])}")
        
        # 工作经历
        work_exp = result['structured_info'].get('work_experience', [])
        print(f"\n工作经历数量: {len(work_exp)}")
        
    except Exception as e:
        print(f"解析失败: {str(e)}")


def example_custom_schema():
    """自定义抽取模式示例 - 根据特定需求定制信息抽取"""
    print("\n\n=== 自定义抽取模式示例 ===\n")
    
    # 自定义抽取模式 - 只关注AI相关经验
    custom_schema = {
        "ai_experience": {
            "ml_projects": [{
                "project_name": "string",
                "algorithms_used": ["string"],
                "business_impact": "string"
            }],
            "dl_frameworks": ["string"],
            "research_papers": [{
                "title": "string",
                "conference": "string",
                "year": "string"
            }],
            "ai_certifications": ["string"]
        },
        "relevant_skills": {
            "programming_languages": ["string"],
            "ml_libraries": ["string"],
            "cloud_platforms": ["string"]
        }
    }
    
    # 创建解析器，使用自定义模式
    parser = ResumeParser(extraction_schema=custom_schema)
    
    # 解析时提供额外指令
    additional_instructions = """
    请特别关注候选人的AI/ML相关经验，包括：
    1. 使用过的深度学习框架
    2. 参与的机器学习项目及其业务影响
    3. 发表的研究论文
    4. 获得的AI相关认证
    """
    
    resume_path = Path("example/ai_engineer_resume.pdf")
    
    try:
        result = parser.parse(
            resume_path,
            additional_instructions=additional_instructions
        )
        
        ai_exp = result['structured_info'].get('ai_experience', {})
        print(f"ML项目数量: {len(ai_exp.get('ml_projects', []))}")
        print(f"深度学习框架: {ai_exp.get('dl_frameworks', [])}")
        
    except Exception as e:
        print(f"解析失败: {str(e)}")


def example_batch_processing():
    """批量处理示例 - 处理多个简历文件"""
    print("\n\n=== 批量处理示例 ===\n")
    
    parser = ResumeParser()
    
    # 准备多个简历文件路径
    resume_files = [
        Path("resumes/candidate1.pdf"),
        Path("resumes/candidate2.docx"),
        Path("resumes/candidate3.md"),
    ]
    
    # 批量解析
    results = parser.parse_batch(resume_files)
    
    # 处理结果
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    
    print(f"成功解析: {len(successful)} 个文件")
    print(f"解析失败: {len(failed)} 个文件")
    
    # 输出失败原因
    for failed_file in failed:
        print(f"\n文件 {failed_file['file_path']} 解析失败:")
        print(f"原因: {failed_file['error']}")


def example_job_specific_extraction():
    """职位特定信息抽取示例 - 为特定职位定制抽取逻辑"""
    print("\n\n=== 职位特定信息抽取示例 ===\n")
    
    # 为前端工程师职位定制的抽取模式
    frontend_schema = {
        "frontend_expertise": {
            "frameworks": {
                "react_experience": {
                    "years": "number",
                    "projects": ["string"],
                    "hooks_proficiency": "boolean"
                },
                "vue_experience": {
                    "years": "number",
                    "version": "string"
                },
                "angular_experience": {
                    "years": "number",
                    "version": "string"
                }
            },
            "ui_libraries": ["string"],
            "css_preprocessors": ["string"],
            "build_tools": ["string"],
            "testing_frameworks": ["string"]
        },
        "portfolio": {
            "github_url": "string",
            "personal_website": "string",
            "notable_projects": [{
                "name": "string",
                "url": "string",
                "tech_stack": ["string"]
            }]
        }
    }
    
    parser = ResumeParser()
    
    # 解析时使用职位特定的模式
    result = parser.parse(
        Path("example/frontend_developer.pdf"),
        custom_schema=frontend_schema,
        additional_instructions="请重点关注前端框架使用经验和实际项目案例"
    )
    
    frontend_exp = result['structured_info'].get('frontend_expertise', {})
    print(f"前端框架经验: {list(frontend_exp.get('frameworks', {}).keys())}")


def example_document_only_parsing():
    """仅文档解析示例 - 不使用LLM，只进行文档格式解析"""
    print("\n\n=== 仅文档解析示例 ===\n")
    
    from interview_agent.core.resume_parser import UniversalDocumentParser
    
    # 创建文档解析器
    doc_parser = UniversalDocumentParser()
    
    # 解析各种格式的文档
    file_paths = [
        Path("example/resume.pdf"),
        Path("example/resume.docx"),
        Path("example/resume.md"),
        Path("example/resume.txt")
    ]
    
    for file_path in file_paths:
        if file_path.exists():
            try:
                parsed_doc = doc_parser.parse(file_path)
                print(f"\n文件: {file_path.name}")
                print(f"格式: {parsed_doc.file_type}")
                print(f"文本长度: {len(parsed_doc.raw_text)} 字符")
                print(f"元数据: {parsed_doc.metadata}")
            except Exception as e:
                print(f"解析 {file_path.name} 失败: {str(e)}")


if __name__ == "__main__":
    # 运行各种示例
    example_basic_usage()
    example_custom_schema()
    example_batch_processing()
    example_job_specific_extraction()
    example_document_only_parsing()
    
    print("\n\n=== 使用建议 ===")
    print("1. 对于标准简历解析，使用默认模式即可")
    print("2. 对于特定职位，可以自定义抽取模式以获得更精准的信息")
    print("3. 可以通过additional_instructions参数提供额外的抽取指导")
    print("4. 支持批量处理多个简历文件")
    print("5. 如果只需要提取文本，可以直接使用UniversalDocumentParser")
"""
面试智能体主程序
"""

from pathlib import Path
from interview_agent.core.resume_parser import ResumeParser
from interview_agent.core.question_generator import QuestionGenerator, JobDescription
from interview_agent.core.interview_conductor import InterviewConductor


def main():
    """主函数"""
    print("=== 面试智能体系统 ===\n")
    
    # 1. 解析候选人简历
    print("1. 解析候选人简历...")
    parser = ResumeParser()
    resume_path = Path("data/zhangjin.md")
    
    if resume_path.exists():
        candidate_profile = parser.parse(resume_path)
        print(f"   候选人：{candidate_profile.name}")
        print(f"   技能：{', '.join(candidate_profile.skills[:5])}...")
        print(f"   经验：{candidate_profile.experience_years}年")
    else:
        print("   简历文件不存在！")
        return
    
    # 2. 定义职位要求（示例）
    job_description = JobDescription(
        title="AI算法工程师",
        requirements=[
            "硕士及以上学历",
            "3年以上算法开发经验",
            "熟悉深度学习框架",
            "了解NLP/CV相关技术"
        ],
        responsibilities=[
            "负责AI算法研发",
            "优化模型性能",
            "参与产品落地"
        ]
    )
    
    # 3. 生成面试题目
    print("\n2. 生成定制化面试题目...")
    generator = QuestionGenerator()
    
    try:
        questions = generator.generate_interview_plan(
            profile=candidate_profile,
            job_description=job_description,
            interviewer_requirements="重点考察算法基础和工程实践能力",
            duration_minutes=30
        )
        
        print(f"   生成了{len(questions)}道题目：")
        for i, q in enumerate(questions):
            print(f"   {i+1}. [{q.type.value}] {q.question[:50]}...")
    
    except Exception as e:
        print(f"   生成题目失败：{e}")
        print("   使用备用题目...")
        questions = generator._generate_fallback_questions(candidate_profile, 30)
        
        print(f"   生成了{len(questions)}道备用题目：")
        for i, q in enumerate(questions):
            print(f"   {i+1}. [{q.type.value}] {q.question[:50]}...")
    
    # 4. 创建面试会话
    print("\n3. 创建面试会话...")
    conductor = InterviewConductor()
    session = conductor.create_session(candidate_profile, questions)
    print(f"   会话ID：{session.id}")
    
    # 5. 开始面试（演示模式）
    print("\n4. 开始面试流程（演示模式）...")
    interviewer_msg = conductor.start_interview(session.id)
    print(f"\n[面试官]: {interviewer_msg}")
    
    print("\n=== 演示结束 ===")
    print("\n提示：")
    print("1. 运行 python example/run_interview_example.py 查看完整的面试示例")
    print("2. 运行 python api/main.py 启动API服务")
    print("3. 确保已配置.env文件中的API密钥")


if __name__ == "__main__":
    main() 
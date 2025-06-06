"""
简化版面试演示 - 基于高柱亮简历生成面试题目
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json

# 添加项目根目录到Python路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# 简化的候选人信息类
class CandidateProfile:
    def __init__(self, name, skills, experience_years, education, work_experience, projects):
        self.name = name
        self.skills = skills
        self.experience_years = experience_years
        self.education = education
        self.work_experience = work_experience
        self.projects = projects

def parse_gaozhuliang_resume():
    """解析高柱亮的简历"""
    return CandidateProfile(
        name="高柱亮",
        skills=[
            "Python", "C++", "SQL", "Java", "深度学习", "NLP", "RAG", 
            "BERT", "GPT", "Deepseek本地化部署", "Elasticsearch", "ELK",
            "分布式存储", "Ceph", "Docker", "Linux", "PyTorch", "TensorFlow",
            "知识图谱", "Neo4j", "数据分析", "机器学习"
        ],
        experience_years=1,  # 2024年7月至今
        education={
            "硕士": "北京科技大学 - 计算机技术（2021-2024）",
            "本科": "北京科技大学 - 信息与计算科学（2017-2021）"
        },
        work_experience=[
            {
                "公司": "季华实验室",
                "职位": "软件工程师",
                "时间": "2024年7月－至今",
                "主要工作": [
                    "实施日志记录策略，整合ELK平台",
                    "本地化部署Deepseek并融合RAG技术",
                    "搭建基于Ceph的分布式存储集群"
                ]
            }
        ],
        projects=[
            {
                "名称": "基于深度学习的智慧分诊管理模型优化策略研究",
                "类型": "国自然基金项目",
                "成果": "发表1篇SCI论文和3篇中文论文",
                "技术": ["BERT改进", "文本分类", "知识图谱", "数据不均衡处理"]
            }
        ]
    )

def generate_interview_questions(candidate, position="算法工程师", duration=45):
    """基于候选人信息生成面试题目"""
    
    questions = []
    
    # 1. 算法基础题（考察基础功底）
    questions.append({
        "type": "算法题",
        "question": "请实现一个LRU缓存机制，要求get和put操作的时间复杂度都是O(1)。同时，请结合您在季华实验室的日志系统经验，说明LRU缓存在实际项目中的应用场景。",
        "duration": 10,
        "difficulty": 3,
        "考察点": ["数据结构", "算法设计", "工程实践"],
        "关联经验": "ELK日志系统优化"
    })
    
    # 2. NLP/大模型问题（考察专业深度）
    questions.append({
        "type": "技术深度题",
        "question": "您提到本地化部署了Deepseek并融合RAG技术。请详细说明：\n1) RAG技术的核心原理和优势\n2) 在代码分析场景中，如何设计检索策略来定位内存泄漏等问题？\n3) 您是如何优化检索效率和准确性的？",
        "duration": 12,
        "difficulty": 4,
        "考察点": ["RAG理解", "大模型应用", "工程优化"],
        "关联经验": "Deepseek本地化部署项目"
    })
    
    # 3. 系统设计题（考察架构能力）
    questions.append({
        "type": "系统设计题",
        "question": "假设您需要设计一个支持百万级医疗文本的智能检索系统，要求：\n1) 支持语义搜索和精确匹配\n2) 响应时间<100ms\n3) 支持实时更新\n请设计系统架构，并说明如何处理您在国自然项目中遇到的数据不均衡问题。",
        "duration": 15,
        "difficulty": 4,
        "考察点": ["系统架构", "性能优化", "实际经验运用"],
        "关联经验": "500万病例数据处理经验"
    })
    
    # 4. 项目经验题（考察实战能力）
    questions.append({
        "type": "项目经验题",
        "question": "在您的国自然基金项目中，处理500万条病例数据时遇到的最大技术挑战是什么？您是如何解决的？如果现在让您重新设计，会有哪些改进？",
        "duration": 8,
        "difficulty": 3,
        "考察点": ["问题解决", "技术决策", "经验总结"],
        "关联经验": "智慧分诊系统项目"
    })
    
    # 5. 开放性问题（考察技术视野）
    questions.append({
        "type": "开放讨论题",
        "question": "结合您的Deepseek部署经验，您如何看待当前大模型在实际工程中的应用？在模型选型、部署优化、成本控制等方面有什么建议？",
        "duration": 10,
        "difficulty": 3,
        "考察点": ["技术理解", "工程思维", "行业认知"],
        "关联经验": "大模型本地化部署"
    })
    
    return questions

def print_interview_plan(candidate, questions):
    """打印面试计划"""
    print("=" * 80)
    print(f"面试候选人：{candidate.name}")
    print(f"目标职位：算法工程师")
    print(f"面试时长：{sum(q['duration'] for q in questions)}分钟")
    print("=" * 80)
    
    print("\n【候选人背景摘要】")
    print(f"- 教育背景：{candidate.education['硕士']}")
    print(f"- 当前职位：{candidate.work_experience[0]['公司']} - {candidate.work_experience[0]['职位']}")
    print(f"- 核心技能：{', '.join(candidate.skills[:10])}...")
    print(f"- 亮点项目：{candidate.projects[0]['名称']}")
    
    print("\n【面试题目安排】")
    for i, q in enumerate(questions, 1):
        print(f"\n{i}. {q['type']} (时长: {q['duration']}分钟, 难度: {'★' * q['difficulty']})")
        print(f"   问题：{q['question']}")
        print(f"   考察点：{', '.join(q['考察点'])}")
        print(f"   关联经验：{q['关联经验']}")
    
    print("\n" + "=" * 80)
    print("【面试注意事项】")
    print("1. 候选人有深度学习研究背景，可深入探讨算法原理")
    print("2. 有实际的大模型部署经验，可考察工程化能力")
    print("3. 参与过大规模数据项目，可讨论性能优化方案")
    print("4. 关注其学习能力和技术热情")
    
    # 保存面试题目到文件
    output_file = f"interview_questions_{candidate.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "候选人": candidate.name,
            "生成时间": datetime.now().isoformat(),
            "题目列表": questions
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n面试题目已保存到：{output_file}")
    print("\n请进行面试，完成后反馈面试过程和候选人表现，我将给出综合评估。")

def main():
    """主函数"""
    print("=== 面试智能体 - 题目生成 ===\n")
    
    # 解析简历
    print("正在解析候选人简历...")
    candidate = parse_gaozhuliang_resume()
    
    # 生成面试题目
    print("正在生成定制化面试题目...")
    questions = generate_interview_questions(candidate)
    
    # 打印面试计划
    print_interview_plan(candidate, questions)

if __name__ == "__main__":
    main() 
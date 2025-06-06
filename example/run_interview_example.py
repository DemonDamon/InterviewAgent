"""
面试智能体示例 - 使用高柱亮的简历进行模拟面试
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from interview_agent.core.resume_parser import ResumeParser
from interview_agent.core.question_generator import QuestionGenerator, JobDescription
from interview_agent.core.interview_conductor import InterviewConductor


def main():
    """运行面试示例"""
    print("=== 面试智能体示例 ===\n")
    
    # 1. 解析候选人简历
    print("1. 解析候选人简历...")
    parser = ResumeParser()
    # 使用绝对路径
    resume_path = project_root / "data" / "gaozhuliang.md"
    
    if not resume_path.exists():
        print(f"简历文件不存在: {resume_path}")
        return
    
    candidate_profile = parser.parse(resume_path)
    print(f"   候选人：{candidate_profile.name}")
    print(f"   技能：{', '.join(candidate_profile.skills[:10])}...")
    print(f"   经验：{candidate_profile.experience_years}年")
    
    # 2. 定义职位要求
    print("\n2. 设置职位要求...")
    job_description = JobDescription(
        title="算法工程师",
        department="AI研发部",
        requirements=[
            "计算机、数学等相关专业硕士及以上学历",
            "3年以上算法开发经验",
            "熟悉Python/C++等编程语言",
            "掌握深度学习框架（PyTorch/TensorFlow）",
            "了解NLP、RAG等AI技术",
            "有大模型应用开发经验优先"
        ],
        responsibilities=[
            "负责AI算法的研发和优化",
            "参与大模型应用的设计和实现",
            "解决工程化部署中的技术难题",
            "与产品团队合作，将AI技术落地"
        ],
        nice_to_have=[
            "有分布式系统开发经验",
            "熟悉Elasticsearch等搜索引擎",
            "了解MLOps相关技术栈"
        ]
    )
    
    # 3. 设置面试官额外要求
    interviewer_requirements = """
    重点考察：
    1. NLP和大模型的实际应用经验，特别是RAG技术
    2. 工程化能力，包括模型部署、性能优化
    3. 分布式存储和日志系统的实践经验
    4. 问题解决能力和学习能力
    
    候选人简历显示有深度学习研究背景和Deepseek本地化部署经验，
    请深入考察其对大模型原理的理解和实际应用能力。
    """
    
    # 4. 生成面试题目
    print("\n3. 生成定制化面试题目...")
    generator = QuestionGenerator()
    
    try:
        questions = generator.generate_interview_plan(
            profile=candidate_profile,
            job_description=job_description,
            interviewer_requirements=interviewer_requirements,
            duration_minutes=45,  # 45分钟面试
            focus_areas=["NLP", "大模型", "工程化", "分布式系统"]
        )
        
        print(f"   生成了{len(questions)}道题目：")
        for i, q in enumerate(questions):
            print(f"   {i+1}. [{q.type.value}] {q.question[:60]}...")
            print(f"      难度：{q.difficulty}/5, 时长：{q.time_minutes}分钟")
    
    except Exception as e:
        print(f"   生成题目时出错：{e}")
        print("   使用备用题目...")
        questions = generator._generate_fallback_questions(candidate_profile, 45)
    
    # 5. 创建面试会话
    print("\n4. 创建面试会话...")
    conductor = InterviewConductor()
    session = conductor.create_session(candidate_profile, questions)
    print(f"   会话ID：{session.id}")
    
    # 6. 开始面试
    print("\n5. 开始面试流程...")
    print("=" * 60)
    interviewer_msg = conductor.start_interview(session.id)
    print(f"\n[面试官]: {interviewer_msg}")
    
    # 7. 模拟面试对话
    print("\n\n=== 模拟面试对话 ===")
    print("(注：以下回答为模拟回答，实际使用时应由真实候选人回答)\n")
    
    # 模拟候选人回答（基于简历内容）
    mock_responses = [
        # 算法题回答
        """我会使用OrderedDict和双向链表来实现LRU Cache。
        具体实现：
        1. 使用OrderedDict存储key-value对，利用其有序特性
        2. get操作：如果key存在，将其移到末尾（最近使用），返回value；否则返回-1
        3. put操作：如果key已存在，更新value并移到末尾；如果是新key且容量已满，删除最早的项
        时间复杂度：get和put都是O(1)
        
        在实际项目中，我在构建日志分析系统时使用过类似的缓存机制来提升查询性能。""",
        
        # NLP/大模型问题
        """关于RAG技术，我有以下理解和实践经验：
        
        RAG（Retrieval-Augmented Generation）结合了检索和生成两个环节：
        1. 检索阶段：将query向量化，从知识库中检索相关文档
        2. 生成阶段：将检索结果作为context，与query一起输入LLM生成答案
        
        在季华实验室，我本地化部署了Deepseek并融合RAG技术：
        - 使用Elasticsearch存储和检索代码文档
        - 通过embedding模型将代码转换为向量
        - 检索相关代码片段作为上下文
        - 帮助定位内存泄漏、指针溢出等问题
        
        关键优化点：
        1. Chunk策略：根据代码结构合理分割
        2. 重排序：使用交叉编码器提升检索质量
        3. 向量索引：使用HNSW算法加速检索""",
        
        # 工程化问题
        """在模型部署方面，我有以下经验：
        
        1. 模型优化：
        - 量化：使用INT8量化减少模型大小
        - 剪枝：移除冗余参数
        - 知识蒸馏：用小模型学习大模型能力
        
        2. 部署架构：
        - 使用TorchServe或TensorFlow Serving
        - 负载均衡：多实例部署，使用Nginx分发请求
        - 缓存策略：对高频请求结果进行缓存
        
        3. 监控和优化：
        - 集成ELK进行日志分析
        - 监控推理延迟、吞吐量等指标
        - 根据负载动态扩缩容
        
        在季华实验室，我负责的日志分析系统就整合了这些技术。""",
        
        # 分布式存储问题
        """我搭建的Ceph分布式存储集群经验：
        
        1. 架构设计：
        - 3个Monitor节点保证高可用
        - 多个OSD节点存储数据
        - 使用CRUSH算法实现数据分布
        
        2. 针对大图片存储的优化：
        - 对象存储：使用RGW提供S3兼容接口
        - 分块上传：大文件分块并行上传
        - 副本策略：根据数据重要性设置副本数
        
        3. 性能优化：
        - SSD缓存层加速热数据访问
        - 网络优化：使用万兆网卡
        - 参数调优：调整PG数量、缓存大小等
        
        这个方案成功支撑了TB级图片数据的存储需求。""",
        
        # 行为面试问题
        """在国自然基金项目中，我遇到的最大挑战是处理500万条病例数据的不均衡问题。
        
        挑战：
        - 某些疾病类别样本极少（<0.1%）
        - 类别之间存在重叠
        - 标注质量参差不齐
        
        解决方案：
        1. 数据层面：SMOTE过采样、数据增强
        2. 算法层面：Focal Loss处理类别不均衡
        3. 模型层面：集成学习提升鲁棒性
        
        通过3个月的迭代优化，最终F1分数提升了15%，论文被SCI收录。
        
        这个经历让我学会了：
        - 系统性分析问题
        - 多角度尝试解决方案
        - 坚持不懈直到取得突破"""
    ]
    
    # 执行模拟对话
    for i, response in enumerate(mock_responses[:len(questions)]):
        print(f"\n[候选人]: {response}")
        
        try:
            interviewer_reply, is_end = conductor.process_candidate_response(
                session.id, response
            )
            print(f"\n[面试官]: {interviewer_reply}")
            
            if is_end:
                break
                
        except Exception as e:
            print(f"\n[系统提示]: 处理回答时出错：{e}")
            # 继续下一题
            session.current_question_index += 1
            if session.current_question_index < len(questions):
                next_q = session.get_current_question()
                print(f"\n[面试官]: 让我们继续下一个问题。\n{conductor._format_question(next_q)}")
            else:
                break
    
    # 8. 生成面试报告
    print("\n\n6. 生成面试报告...")
    print("=" * 60)
    
    try:
        report = conductor.get_session_report(session.id)
        
        print("\n=== 面试评估报告 ===")
        print(f"候选人：{report['candidate']['name']}")
        print(f"面试时长：{report['duration_minutes']:.1f}分钟")
        print(f"回答题目：{report['questions_asked']}道")
        print(f"总体评分：{report['overall_score']:.1f}/5.0")
        
        print(f"\n主要优势：")
        for strength in report['strengths']:
            print(f"  ✓ {strength}")
        
        print(f"\n待改进领域：")
        for improvement in report['areas_for_improvement']:
            print(f"  - {improvement}")
        
        print(f"\n录用建议：{report['recommendation']}")
        
        # 详细评估
        print("\n\n=== 各题目评估详情 ===")
        for q_id, eval_data in report['evaluations'].items():
            question = next((q for q in questions if q.id == q_id), None)
            if question:
                print(f"\n题目{q_id}: {question.question[:50]}...")
                print(f"得分: {eval_data.get('score', 'N/A')}/5")
                if 'analysis' in eval_data:
                    analysis = eval_data['analysis']
                    print(f"技术深度: {'是' if analysis.get('technical_depth') else '否'}")
                    print(f"完整性: {'是' if analysis.get('completeness') else '否'}")
                    
    except Exception as e:
        print(f"生成报告时出错：{e}")
    
    print("\n\n=== 面试示例结束 ===")


if __name__ == "__main__":
    main() 
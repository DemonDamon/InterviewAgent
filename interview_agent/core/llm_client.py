"""
统一的LLM客户端 - 支持通过wildcard API调用各种模型
"""

import json
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
import httpx


@dataclass
class Message:
    """消息结构"""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """LLM响应结构"""
    content: str
    model: str
    usage: Dict[str, int]
    raw_response: Dict


class WildcardLLMClient:
    """Wildcard API统一客户端"""
    
    def __init__(self, 
                 api_key: str,
                 api_base: str,
                 model: str,
                 temperature: float = 0.7,
                 max_tokens: int = 2000):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        if not self.api_key:
            raise ValueError("Wildcard API key not provided")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(self,
                       messages: List[Union[Message, Dict]],
                       model: Optional[str] = None,
                       temperature: Optional[float] = None,
                       max_tokens: Optional[int] = None,
                       stream: bool = False,
                       **kwargs) -> LLMResponse:
        """统一的聊天补全接口"""
        
        # 处理消息格式
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, Message):
                formatted_messages.append({"role": msg.role, "content": msg.content})
            else:
                formatted_messages.append(msg)
        
        # 构建请求体
        payload = {
            "model": model or self.model,
            "messages": formatted_messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": stream,
            **kwargs
        }
        
        # 发送请求
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.api_base}/v1/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                
                data = response.json()
                
                # 提取响应内容
                content = data["choices"][0]["message"]["content"]
                
                return LLMResponse(
                    content=content,
                    model=data.get("model", model or self.model),
                    usage=data.get("usage", {}),
                    raw_response=data
                )
                
        except httpx.RequestError as e:
            raise Exception(f"API请求失败: {str(e)}")
        except Exception as e:
            raise Exception(f"处理响应时出错: {str(e)}")
    
    def generate_interview_questions(self,
                                   candidate_info: str,
                                   job_description: str,
                                   interview_requirements: str,
                                   duration_minutes: int) -> str:
        """生成面试题目的专用方法"""
        
        system_prompt = """你是一位经验丰富的技术面试官。请根据候选人简历、职位要求和面试官的额外要求，
生成一套完整的面试题目方案。

面试应该包含以下几个核心环节：
1. 算法原理考察 - 评估候选人的算法基础和理论功底
2. 工程实践能力 - 考察实际项目经验和问题解决能力
3. AI开放性问题 - 测试对AI技术的理解深度和迁移应用能力
4. 软技能评估 - 了解团队协作、沟通和学习能力

请确保：
- 题目难度与候选人经验相匹配
- 题目与职位要求高度相关
- 时间分配合理，总时长控制在指定范围内
- 每道题都包含评估要点和参考答案要点
"""

        user_prompt = f"""请为以下候选人生成面试题目：

【候选人信息】
{candidate_info}

【职位要求】
{job_description}

【面试官额外要求】
{interview_requirements}

【面试时长】
{duration_minutes}分钟

请生成详细的面试题目列表，包括：
1. 每道题的具体内容
2. 预计用时
3. 评估要点
4. 参考答案要点
5. 可能的追问方向

请以JSON格式输出。"""

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        response = self.chat_completion(messages)
        return response.content
    
    def analyze_answer(self,
                      question: str,
                      answer: str,
                      evaluation_criteria: List[str]) -> Dict:
        """分析候选人答案"""
        
        prompt = f"""请分析候选人对以下问题的回答：

【问题】
{question}

【候选人回答】
{answer}

【评估标准】
{', '.join(evaluation_criteria)}

请从以下维度进行分析：
1. 答案的完整性和准确性
2. 技术深度
3. 表达清晰度
4. 是否需要追问或澄清
5. 综合评分（1-5分）

请以JSON格式返回分析结果。"""

        messages = [
            Message(role="system", content="你是一位专业的技术面试官，擅长评估候选人的技术能力。"),
            Message(role="user", content=prompt)
        ]
        
        response = self.chat_completion(messages)
        
        try:
            return json.loads(response.content)
        except:
            # 如果JSON解析失败，返回基础分析
            return {
                "completeness": True,
                "technical_depth": True,
                "clarity": True,
                "needs_clarification": False,
                "score": 3,
                "feedback": response.content
            }
    
    def generate_follow_up(self,
                         question: str,
                         answer: str,
                         context: str) -> str:
        """生成追问问题"""
        
        prompt = f"""基于候选人的回答，生成一个合适的追问问题：

【原问题】
{question}

【候选人回答】
{answer}

【上下文】
{context}

请生成一个深入的追问，帮助更好地评估候选人的能力。追问应该：
1. 基于候选人的回答内容
2. 探索更深层次的理解
3. 或者澄清不明确的部分

只返回追问问题本身，不需要其他说明。"""

        messages = [
            Message(role="system", content="你是一位经验丰富的面试官。"),
            Message(role="user", content=prompt)
        ]
        
        response = self.chat_completion(messages)
        return response.content.strip()
    
    def web_search(self, query: str) -> str:
        """联网搜索功能（如果API支持）"""
        # 某些模型支持联网搜索，这里提供接口
        messages = [
            Message(role="system", content="请搜索并总结相关信息。"),
            Message(role="user", content=f"搜索：{query}")
        ]
        
        response = self.chat_completion(messages)
        return response.content


# 不再创建全局LLM客户端实例，由各个agent负责创建 
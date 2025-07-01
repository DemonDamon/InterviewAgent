"""
Interview Agent Core Modules
"""

from .resume_parser import ResumeParser, ParsedDocument, UniversalDocumentParser
from .question_generator import QuestionGenerator, InterviewQuestion, QuestionType, JobDescription
from .interview_conductor import InterviewConductor, InterviewSession, InterviewState
from .llm_client import WildcardLLMClient, Message
from .vector_store import VectorStore, MilvusStore, QdrantStore, VectorStoreFactory, Document
from .base_agent import (
    BaseAgent, AgentContext, AgentStatus, AgentMessage, MessageType,
    ChainAgent, ConditionalAgent, LoopAgent
)
# 条件导入音频处理模块
try:
    from .audio_handler import AudioManager, AudioHandler
    _AUDIO_AVAILABLE = True
except ImportError:
    AudioManager = None
    AudioHandler = None
    _AUDIO_AVAILABLE = False

__all__ = [
    # 简历解析
    "ResumeParser",
    "ParsedDocument",
    "UniversalDocumentParser",
    
    # 题目生成
    "QuestionGenerator", 
    "InterviewQuestion",
    "QuestionType",
    "JobDescription",
    
    # 面试执行
    "InterviewConductor",
    "InterviewSession",
    "InterviewState",
    
    # LLM客户端
    "WildcardLLMClient",
    "llm_client",
    "Message",
    
    # 向量存储
    "VectorStore",
    "MilvusStore",
    "QdrantStore",
    "VectorStoreFactory",
    "Document",
    
    # Agent基类
    "BaseAgent",
    "AgentContext",
    "AgentStatus",
    "AgentMessage",
    "MessageType",
    "ChainAgent",
    "ConditionalAgent",
    "LoopAgent"
]

# 条件性添加音频处理模块
if _AUDIO_AVAILABLE:
    __all__.extend(["AudioManager", "AudioHandler"]) 
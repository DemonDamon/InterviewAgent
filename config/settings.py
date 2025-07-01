"""
配置管理模块
"""

import os
from typing import Optional
try:
    # Pydantic v2
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    # Pydantic v1
    from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings(BaseSettings):
    """应用配置"""
    
    # Wildcard API配置
    wildcard_api_key: str = Field(default="", env="WILDCARD_API_KEY")
    wildcard_api_base: str = Field(default="https://api.gptsapi.net", env="WILDCARD_API_BASE")
    
    # HTTP代理配置（用于解决SSL问题）
    http_proxy: Optional[str] = Field(default=None, env="HTTP_PROXY")
    https_proxy: Optional[str] = Field(default=None, env="HTTPS_PROXY")
    verify_ssl: bool = Field(default=False, env="VERIFY_SSL")
    
    # LLM通用配置
    llm_provider: str = Field("wildcard", env="LLM_PROVIDER")  # wildcard, openai, anthropic
    llm_model: str = Field("claude-3-5-sonnet-20241022", env="LLM_MODEL")
    llm_temperature: float = Field(0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(2000, env="LLM_MAX_TOKENS")
    
    # 各Agent的LLM参数配置
    planner_temperature: float = Field(0.7, env="PLANNER_TEMPERATURE")
    planner_max_tokens: int = Field(3000, env="PLANNER_MAX_TOKENS")
    
    parser_temperature: float = Field(0.1, env="PARSER_TEMPERATURE")
    parser_max_tokens: int = Field(2000, env="PARSER_MAX_TOKENS")
    
    evaluator_temperature: float = Field(0.3, env="EVALUATOR_TEMPERATURE")
    evaluator_max_tokens: int = Field(2000, env="EVALUATOR_MAX_TOKENS")
    
    executor_temperature: float = Field(0.7, env="EXECUTOR_TEMPERATURE")
    executor_max_tokens: int = Field(2000, env="EXECUTOR_MAX_TOKENS")
    
    # 数据库配置
    database_url: str = Field(
        "postgresql://user:password@localhost/interview_db",
        env="DATABASE_URL"
    )
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    
    # 向量数据库配置
    vector_db_type: str = Field("milvus", env="VECTOR_DB_TYPE")  # milvus, qdrant
    
    # Milvus配置
    milvus_host: str = Field("localhost", env="MILVUS_HOST")
    milvus_port: int = Field(19530, env="MILVUS_PORT")
    milvus_collection_name: str = Field("interview_questions", env="MILVUS_COLLECTION")
    
    # Qdrant配置（保留兼容性）
    qdrant_url: str = Field("http://localhost:6333", env="QDRANT_URL")
    
    # 应用配置
    app_name: str = "Interview Agent"
    app_version: str = "0.1.0"
    debug: bool = Field(False, env="DEBUG")
    
    # 面试配置
    default_interview_duration: int = Field(30, env="DEFAULT_INTERVIEW_DURATION")
    max_questions_per_interview: int = Field(10, env="MAX_QUESTIONS_PER_INTERVIEW")
    
    # 简历处理配置
    resume_max_length: int = Field(16000, env="RESUME_MAX_LENGTH")
    
    # 文件存储
    upload_dir: str = Field("./uploads", env="UPLOAD_DIR")
    max_file_size: int = Field(10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    
    # 火山引擎语音服务配置
    volc_app_id: str = Field("", env="VOLC_APP_ID")
    volc_access_key: str = Field("", env="VOLC_ACCESS_KEY")
    volc_resource_id: str = Field("volc.speech.dialog", env="VOLC_RESOURCE_ID")
    volc_app_key: str = Field("PlgvMymc7f3tQnJ6", env="VOLC_APP_KEY")  # 固定值
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Pydantic v2 兼容性
        extra = "ignore"


# 创建全局配置实例
settings = Settings()


# 配置示例文件内容
EXAMPLE_ENV_CONTENT = """
# Wildcard API配置
WILDCARD_API_KEY=sk-vwR14fbdd9364638da79456d0c24ddcba432d1aa2172RMzu
WILDCARD_API_BASE=https://api.gptsapi.net

# LLM通用配置
LLM_PROVIDER=wildcard
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=16000

# Agent特定LLM参数
PLANNER_TEMPERATURE=0.7
PLANNER_MAX_TOKENS=3000
PARSER_TEMPERATURE=0.1
PARSER_MAX_TOKENS=2000
EVALUATOR_TEMPERATURE=0.3
EVALUATOR_MAX_TOKENS=2000
EXECUTOR_TEMPERATURE=0.7
EXECUTOR_MAX_TOKENS=2000

# Database
DATABASE_URL=postgresql://user:password@localhost/interview_db
REDIS_URL=redis://localhost:6379

# Vector Database
VECTOR_DB_TYPE=milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=interview_questions
QDRANT_URL=http://localhost:6333

# 面试配置
DEFAULT_INTERVIEW_DURATION=30
MAX_QUESTIONS_PER_INTERVIEW=10
RESUME_MAX_LENGTH=16000

# 音频配置
TTS_BACKEND=edge
STT_BACKEND=openai

# 文件存储
UPLOAD_DIR=./uploads
REPORT_DIR=./reports
MAX_FILE_SIZE=10485760

# 火山引擎语音服务配置
VOLC_APP_ID=your_app_id
VOLC_ACCESS_KEY=your_access_key
VOLC_RESOURCE_ID=volc.speech.dialog
VOLC_APP_KEY=PlgvMymc7f3tQnJ6

# 应用配置
DEBUG=false
PORT=7860
LOG_LEVEL=INFO
"""


def create_env_example():
    """创建.env.example文件"""
    with open(".env.example", "w") as f:
        f.write(EXAMPLE_ENV_CONTENT.strip())
    print("Created .env.example file") 
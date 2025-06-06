"""
配置示例文件
请将此文件复制为 ../.env 并填入您的实际配置
"""

# 示例环境变量配置
ENV_EXAMPLE = """
# Wildcard API配置
WILDCARD_API_KEY=sk-vwR14fbdd9364638da79456d0c24ddcba432d1aa2172RMzu
WILDCARD_API_BASE=https://api.gptsapi.net

# LLM Configuration
LLM_PROVIDER=wildcard
LLM_MODEL=claude-3-5-sonnet-20241022  # 可选其他模型如 gpt-4, gemini-2.5-pro-preview-03-25 等
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Vector Database
VECTOR_DB_TYPE=milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=interview_questions

# 其他配置
DEBUG=false
DEFAULT_INTERVIEW_DURATION=30
MAX_QUESTIONS_PER_INTERVIEW=10
"""

# 支持的模型列表
SUPPORTED_MODELS = {
    "claude": [
        "claude-3-7-sonnet-20250219",
        "claude-3-5-sonnet-20241022",
        "claude-opus-4-20250514",
        "claude-sonnet-4-20250514"
    ],
    "openai": [
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo"
    ],
    "gemini": [
        "gemini-2.5-pro-preview-03-25",
        "gemini-2.5-flash-preview"
    ]
}

def create_env_file():
    """创建.env文件"""
    import os
    env_path = os.path.join(os.path.dirname(__file__), "../.env")
    
    if os.path.exists(env_path):
        print(f".env文件已存在: {env_path}")
        return
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(ENV_EXAMPLE.strip())
    
    print(f"已创建.env文件: {env_path}")
    print("请编辑该文件并填入您的API密钥")

if __name__ == "__main__":
    create_env_file() 
"""
面试智能体快速开始脚本
"""

import os
import sys
from pathlib import Path


def check_env():
    """检查环境配置"""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("❌ 未找到.env文件")
        print("\n正在创建.env文件...")
        
        # 创建.env文件
        env_content = """# Wildcard API配置
WILDCARD_API_KEY=sk-vwR14fbdd9364638da79456d0c24ddcba432d1aa2172RMzu
WILDCARD_API_BASE=https://api.gptsapi.net

# LLM Configuration
LLM_PROVIDER=wildcard
LLM_MODEL=claude-3-5-sonnet-20241022
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Vector Database (可选)
VECTOR_DB_TYPE=milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 其他配置
DEBUG=false
DEFAULT_INTERVIEW_DURATION=30
MAX_QUESTIONS_PER_INTERVIEW=10"""
        
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("✅ 已创建.env文件")
        print("⚠️  请编辑.env文件，填入您的Wildcard API密钥")
        return False
    
    # 检查API密钥
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("WILDCARD_API_KEY", "")
    if not api_key or api_key.startswith("sk-your"):
        print("❌ 请在.env文件中设置有效的WILDCARD_API_KEY")
        return False
    
    print("✅ 环境配置正常")
    return True


def check_dependencies():
    """检查依赖"""
    required_packages = [
        "fastapi",
        "uvicorn",
        "httpx",
        "pydantic",
        "python-dotenv"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少以下依赖包：{', '.join(missing_packages)}")
        print("\n请运行以下命令安装依赖：")
        print("pip install -r requirements.txt")
        return False
    
    print("✅ 依赖检查通过")
    return True


def main():
    """主函数"""
    print("=== 面试智能体快速开始 ===\n")
    
    # 1. 检查环境
    print("1. 检查环境配置...")
    if not check_env():
        return
    
    # 2. 检查依赖
    print("\n2. 检查依赖包...")
    if not check_dependencies():
        return
    
    # 3. 选择运行模式
    print("\n3. 请选择运行模式：")
    print("   [1] 运行完整示例（推荐）")
    print("   [2] 启动API服务")
    print("   [3] 运行简单演示")
    print("   [4] 查看使用说明")
    
    choice = input("\n请输入选项 (1-4): ").strip()
    
    if choice == "1":
        print("\n正在运行完整示例...")
        os.system(f"{sys.executable} example/run_interview_example.py")
    
    elif choice == "2":
        print("\n正在启动API服务...")
        print("API文档地址: http://localhost:8000/docs")
        os.system(f"{sys.executable} -m uvicorn api.main:app --reload")
    
    elif choice == "3":
        print("\n正在运行简单演示...")
        os.system(f"{sys.executable} main.py")
    
    elif choice == "4":
        print("\n=== 使用说明 ===")
        print("\n1. 完整示例：")
        print("   - 展示完整的面试流程")
        print("   - 包括简历解析、题目生成、模拟对话、评估报告")
        print("   - 使用高柱亮的简历作为示例")
        
        print("\n2. API服务：")
        print("   - 提供RESTful API接口")
        print("   - 支持上传简历、生成题目、进行面试")
        print("   - 访问 http://localhost:8000/docs 查看API文档")
        
        print("\n3. 简单演示：")
        print("   - 快速展示系统基本功能")
        print("   - 不包含实际对话过程")
        
        print("\n更多信息请查看 README.md 和 example/README.md")
    
    else:
        print("\n无效的选项")


if __name__ == "__main__":
    main() 
#!/usr/bin/env python
"""
面试智能体启动脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
os.environ["GRADIO_SERVER_NAME"] = "0.0.0.0"

# 导入并运行应用
from app import demo

if __name__ == "__main__":
    print("🚀 启动AI面试智能体系统...")
    print("📌 访问地址: http://localhost:7860")
    print("💡 提示: 使用 Ctrl+C 停止服务器")
    
    try:
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,  # 设置为True可以生成公共链接
            inbrowser=True  # 自动打开浏览器
        )
    except KeyboardInterrupt:
        print("\n👋 服务器已停止") 
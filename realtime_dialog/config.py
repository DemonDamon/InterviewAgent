import uuid
import pyaudio
import os
from pathlib import Path
from dotenv import load_dotenv

# 获取项目根目录路径并加载 .env 文件
current_dir = Path(__file__).parent
project_root = current_dir.parent
env_path = project_root / '.env'

# 从项目根目录的 .env 文件加载环境变量
load_dotenv(env_path)

# 配置信息
ws_connect_config = {
    "base_url": "wss://openspeech.bytedance.com/api/v3/realtime/dialogue",
    "headers": {
        "X-Api-App-ID": os.getenv("VOLC_APP_ID", "YOUR_VOLC_APP_ID"),
        "X-Api-Access-Key": os.getenv("VOLC_ACCESS_KEY", "YOUR_VOLC_ACCESS_KEY"),
        "X-Api-Resource-Id": os.getenv("VOLC_RESOURCE_ID", "volc.speech.dialog"),
        "X-Api-App-Key": "PlgvMymc7f3tQnJ6",  # 固定值，根据官方文档
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }
}

start_session_req = {
    "tts": {
        "audio_config": {
            "channel": 1,
            "format": "pcm",
            "sample_rate": 24000
        },
    },
    "dialog": {
        "bot_name": "豆包",
    }
}

input_audio_config = {
    "chunk": 3200,
    "format": "pcm",
    "channels": 1,
    "sample_rate": 16000,
    "bit_size": pyaudio.paInt16
}

output_audio_config = {
    "chunk": 3200,
    "format": "pcm",
    "channels": 1,
    "sample_rate": 24000,
    "bit_size": pyaudio.paFloat32
}

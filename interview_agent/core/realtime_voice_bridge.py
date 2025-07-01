"""
实时语音桥接器 - 使用集成的语音服务模块
"""

import asyncio
import uuid
from typing import Dict, Optional, Callable
import logging

from .voice_audio_manager import IntegratedVoiceSession
from config.settings import settings


class RealtimeVoiceBridge:
    """实时语音桥接器"""
    
    def __init__(self, 
                 on_text_received: Callable[[str], None] = None,
                 on_audio_received: Callable[[bytes], None] = None):
        self.logger = logging.getLogger(__name__)
        self.on_text_received = on_text_received
        self.on_audio_received = on_audio_received
        
        # 语音会话
        self.voice_session: Optional[IntegratedVoiceSession] = None
        self.is_connected = False
        self.is_running = False
        
        # 加载配置
        self._load_config()
    
    def _load_config(self):
        """加载语音服务配置"""
        # 语音服务配置
        self.voice_config = {
            "base_url": "wss://openspeech.bytedance.com/api/v3/realtime/dialogue",
            "headers": {
                "X-Api-App-ID": settings.volc_app_id,
                "X-Api-Access-Key": settings.volc_access_key,
                "X-Api-Resource-Id": settings.volc_resource_id,
                "X-Api-App-Key": settings.volc_app_key,
                "X-Api-Connect-Id": str(uuid.uuid4()),
            }
        }
        
        # 会话配置
        self.session_config = {
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
    
    async def start(self) -> bool:
        """启动语音桥接器"""
        try:
            self.logger.info("启动实时语音桥接器")
            
            # 创建语音会话
            self.voice_session = IntegratedVoiceSession(
                voice_config=self.voice_config,
                session_config=self.session_config,
                on_text_received=self._on_text_received,
                on_audio_received=self._on_audio_received
            )
            
            # 启动会话
            success = await self.voice_session.start()
            
            if success:
                self.is_connected = True
                self.is_running = True
                self.logger.info("实时语音桥接器启动成功")
                return True
            else:
                self.logger.error("语音会话启动失败")
                return False
                
        except Exception as e:
            self.logger.error(f"启动语音桥接器失败: {e}")
            return False
    
    async def stop(self):
        """停止语音桥接器"""
        try:
            self.is_running = False
            
            if self.voice_session:
                await self.voice_session.stop()
                
            self.is_connected = False
            self.logger.info("语音桥接器已停止")
            
        except Exception as e:
            self.logger.error(f"停止语音桥接器失败: {e}")
    
    async def send_text(self, text: str):
        """发送文本进行语音合成"""
        try:
            if not self.voice_session or not self.is_connected:
                self.logger.warning("语音服务未连接，无法发送文本")
                return
            
            await self.voice_session.send_text_for_speech(text)
            
        except Exception as e:
            self.logger.error(f"发送文本失败: {e}")
    
    async def send_audio(self, audio_data: bytes):
        """发送音频数据进行识别"""
        try:
            if not self.voice_session or not self.is_connected:
                self.logger.warning("语音服务未连接，无法发送音频")
                return
            
            # 注意：在集成版本中，音频录制是自动进行的
            # 这个方法主要用于外部音频输入
            self.logger.debug(f"收到外部音频数据: {len(audio_data)} bytes")
            
        except Exception as e:
            self.logger.error(f"处理音频失败: {e}")
    
    def _on_text_received(self, text: str):
        """收到文本回调"""
        self.logger.info(f"收到识别文本: {text}")
        if self.on_text_received:
            self.on_text_received(text)
    
    def _on_audio_received(self, audio_data: bytes):
        """收到音频回调"""
        self.logger.debug(f"收到音频数据: {len(audio_data)} bytes")
        if self.on_audio_received:
            self.on_audio_received(audio_data)
    
    def get_status(self) -> Dict:
        """获取状态"""
        base_status = {
            "is_connected": self.is_connected,
            "is_running": self.is_running,
            "has_realtime_module": True  # 现在总是可用
        }
        
        if self.voice_session:
            base_status.update(self.voice_session.get_status())
        
        return base_status 
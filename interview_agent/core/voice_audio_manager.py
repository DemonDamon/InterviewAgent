"""
语音音频管理模块 - 处理音频输入输出和设备管理
"""

import asyncio
import queue
import threading
import time
import logging
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import os

# 尝试导入pyaudio，如果不可用则使用模拟模式
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
    logging.info("PyAudio可用，支持实时音频处理")
except ImportError:
    pyaudio = None
    PYAUDIO_AVAILABLE = False
    logging.info("PyAudio不可用，将使用模拟音频模式（语音服务仍可正常工作）")

from .voice_client import VoiceServiceClient
from .voice_protocol import VoiceMessage


@dataclass
class AudioConfig:
    """音频配置"""
    format: str
    bit_size: int
    channels: int
    sample_rate: int
    chunk: int


class AudioDeviceManager:
    """音频设备管理器"""
    
    def __init__(self, input_config: AudioConfig, output_config: AudioConfig):
        self.input_config = input_config
        self.output_config = output_config
        self.logger = logging.getLogger(__name__)
        
        # PyAudio实例
        self.pyaudio_instance = None
        self.input_stream: Optional[object] = None
        self.output_stream: Optional[object] = None
        
        # 初始化PyAudio
        if PYAUDIO_AVAILABLE:
            try:
                self.pyaudio_instance = pyaudio.PyAudio()
                self.logger.info("PyAudio初始化成功")
            except Exception as e:
                self.logger.error(f"PyAudio初始化失败: {e}")
                self.pyaudio_instance = None
        else:
            self.logger.info("使用模拟音频模式")
    
    def open_input_stream(self):
        """打开音频输入流"""
        if not PYAUDIO_AVAILABLE or not self.pyaudio_instance:
            self.logger.info("模拟打开音频输入流")
            return None
        
        try:
            self.input_stream = self.pyaudio_instance.open(
                format=self.input_config.bit_size,
                channels=self.input_config.channels,
                rate=self.input_config.sample_rate,
                input=True,
                frames_per_buffer=self.input_config.chunk
            )
            self.logger.info("音频输入流已打开")
            return self.input_stream
        except Exception as e:
            self.logger.error(f"打开音频输入流失败: {e}")
            return None
    
    def open_output_stream(self):
        """打开音频输出流"""
        if not PYAUDIO_AVAILABLE or not self.pyaudio_instance:
            self.logger.info("模拟打开音频输出流")
            return None
        
        try:
            self.output_stream = self.pyaudio_instance.open(
                format=self.output_config.bit_size,
                channels=self.output_config.channels,
                rate=self.output_config.sample_rate,
                output=True,
                frames_per_buffer=self.output_config.chunk
            )
            self.logger.info("音频输出流已打开")
            return self.output_stream
        except Exception as e:
            self.logger.error(f"打开音频输出流失败: {e}")
            return None
    
    def cleanup(self):
        """清理音频设备资源"""
        try:
            if self.input_stream:
                self.input_stream.stop_stream()
                self.input_stream.close()
                self.input_stream = None
            
            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
                self.output_stream = None
            
            if self.pyaudio_instance:
                self.pyaudio_instance.terminate()
                self.pyaudio_instance = None
            
            self.logger.info("音频设备资源已清理")
        except Exception as e:
            self.logger.error(f"清理音频设备失败: {e}")


class IntegratedVoiceSession:
    """集成语音会话管理器"""
    
    def __init__(self, 
                 voice_config: Dict[str, Any],
                 session_config: Dict[str, Any],
                 on_text_received: Callable[[str], None] = None,
                 on_audio_received: Callable[[bytes], None] = None):
        
        self.voice_config = voice_config
        self.session_config = session_config
        self.on_text_received_callback = on_text_received
        self.on_audio_received_callback = on_audio_received
        
        self.logger = logging.getLogger(__name__)
        
        # 语音客户端
        self.voice_client = VoiceServiceClient(voice_config)
        self.voice_client.on_message_received = self._handle_voice_message
        
        # 音频设备管理
        input_config = AudioConfig(
            format="pcm",
            bit_size=pyaudio.paInt16 if PYAUDIO_AVAILABLE else 16,
            channels=1,
            sample_rate=16000,
            chunk=3200
        )
        
        output_config = AudioConfig(
            format="pcm", 
            bit_size=pyaudio.paFloat32 if PYAUDIO_AVAILABLE else 32,
            channels=1,
            sample_rate=24000,
            chunk=3200
        )
        
        self.audio_device = AudioDeviceManager(input_config, output_config)
        
        # 音频队列和线程
        self.audio_queue = queue.Queue()
        self.output_stream = None
        self.player_thread: Optional[threading.Thread] = None
        self.recorder_thread: Optional[threading.Thread] = None
        
        # 状态控制
        self.is_running = False
        self.is_recording = False
        self.is_playing = False
    
    async def start(self) -> bool:
        """启动语音会话"""
        try:
            self.logger.info("启动集成语音会话")
            
            # 连接语音服务
            if not await self.voice_client.connect():
                return False
            
            # 启动语音会话
            if not await self.voice_client.start_session(self.session_config):
                return False
            
            # 初始化音频设备
            self.output_stream = self.audio_device.open_output_stream()
            
            # 启动音频处理线程
            self.is_running = True
            self.is_recording = True
            self.is_playing = True
            
            # 启动播放线程
            self.player_thread = threading.Thread(target=self._audio_player_loop)
            self.player_thread.daemon = True
            self.player_thread.start()
            
            # 启动录音线程
            self.recorder_thread = threading.Thread(target=self._audio_recorder_loop)
            self.recorder_thread.daemon = True
            self.recorder_thread.start()
            
            # 启动消息接收
            asyncio.create_task(self.voice_client.receive_messages())
            
            self.logger.info("集成语音会话启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"启动语音会话失败: {e}")
            return False
    
    async def stop(self):
        """停止语音会话"""
        try:
            self.logger.info("停止集成语音会话")
            
            # 停止录音和播放
            self.is_running = False
            self.is_recording = False
            self.is_playing = False
            
            # 等待线程结束
            if self.player_thread and self.player_thread.is_alive():
                self.player_thread.join(timeout=2.0)
            
            if self.recorder_thread and self.recorder_thread.is_alive():
                self.recorder_thread.join(timeout=2.0)
            
            # 结束语音会话
            await self.voice_client.finish_session()
            await self.voice_client.disconnect()
            
            # 清理音频设备
            self.audio_device.cleanup()
            
            self.logger.info("集成语音会话已停止")
            
        except Exception as e:
            self.logger.error(f"停止语音会话失败: {e}")
    
    async def send_text_for_speech(self, text: str):
        """发送文本进行语音合成"""
        try:
            await self.voice_client.send_text(text)
        except Exception as e:
            self.logger.error(f"发送文本失败: {e}")
    
    def _audio_player_loop(self):
        """音频播放线程循环"""
        self.logger.info("启动音频播放线程")
        
        while self.is_playing:
            try:
                # 从队列获取音频数据
                audio_data = self.audio_queue.get(timeout=1.0)
                
                if audio_data and self.output_stream:
                    if PYAUDIO_AVAILABLE:
                        self.output_stream.write(audio_data)
                    else:
                        # 模拟播放
                        self.logger.debug(f"模拟播放音频: {len(audio_data)} bytes")
                        
            except queue.Empty:
                # 队列为空时短暂休眠
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"音频播放错误: {e}")
                time.sleep(0.1)
        
        self.logger.info("音频播放线程已停止")
    
    def _audio_recorder_loop(self):
        """音频录制线程循环"""
        self.logger.info("启动音频录制线程")
        
        input_stream = self.audio_device.open_input_stream()
        if not input_stream and PYAUDIO_AVAILABLE:
            self.logger.error("无法打开音频输入流")
            return
        
        while self.is_recording:
            try:
                if PYAUDIO_AVAILABLE and input_stream:
                    # 读取音频数据
                    audio_data = input_stream.read(
                        self.audio_device.input_config.chunk,
                        exception_on_overflow=False
                    )
                    
                    # 发送到语音服务
                    asyncio.run_coroutine_threadsafe(
                        self.voice_client.send_audio(audio_data),
                        asyncio.get_event_loop()
                    )
                else:
                    # 模拟录音
                    time.sleep(0.2)  # 模拟录音间隔
                    
            except Exception as e:
                self.logger.error(f"音频录制错误: {e}")
                time.sleep(0.1)
        
        self.logger.info("音频录制线程已停止")
    
    async def _handle_voice_message(self, message: VoiceMessage):
        """处理语音消息"""
        try:
            if message.message_type == 'SERVER_ACK' and isinstance(message.payload_msg, bytes):
                # 收到音频数据
                self.audio_queue.put(message.payload_msg)
                
                if self.on_audio_received_callback:
                    self.on_audio_received_callback(message.payload_msg)
                    
            elif message.message_type == 'SERVER_FULL_RESPONSE':
                self.logger.info(f"收到服务器响应: {message.payload_msg}")
                
                # 检查是否包含文本内容
                if (isinstance(message.payload_msg, dict) and 
                    'text' in message.payload_msg):
                    text_content = message.payload_msg['text']
                    if self.on_text_received_callback:
                        self.on_text_received_callback(text_content)
                
                # 处理特殊事件
                if message.event == 450:  # 清空音频缓存
                    self.logger.info("清空音频缓存")
                    while not self.audio_queue.empty():
                        try:
                            self.audio_queue.get_nowait()
                        except queue.Empty:
                            break
                            
            elif message.message_type == 'SERVER_ERROR':
                self.logger.error(f"服务器错误: {message.payload_msg}")
                
        except Exception as e:
            self.logger.error(f"处理语音消息失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取会话状态"""
        return {
            "is_running": self.is_running,
            "is_recording": self.is_recording,
            "is_playing": self.is_playing,
            "voice_client_status": self.voice_client.get_status(),
            "audio_available": PYAUDIO_AVAILABLE
        } 
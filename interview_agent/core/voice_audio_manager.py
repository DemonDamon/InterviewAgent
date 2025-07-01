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
import concurrent.futures

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
        
        self.logger = logging.getLogger(__name__)
        self.voice_config = voice_config
        self.session_config = session_config
        
        # 回调函数
        self.on_text_received_callback = on_text_received
        self.on_audio_received_callback = on_audio_received
        
        # 语音客户端
        self.voice_client = VoiceServiceClient(
            config=voice_config,
            session_id=None
        )
        self.voice_client.on_message_received = self._handle_voice_message
        
        # 音频设备配置
        input_config = AudioConfig(
            format="pcm",
            bit_size=pyaudio.paInt16 if PYAUDIO_AVAILABLE else 16,
            channels=1,
            sample_rate=16000,
            chunk=1600
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
        
        # 保存主事件循环引用
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None
    
    async def start(self) -> bool:
        """启动语音会话"""
        try:
            self.logger.info("启动集成语音会话")
            
            # 保存当前事件循环引用
            self.main_loop = asyncio.get_running_loop()
            
            # 连接语音服务
            if not await self.voice_client.connect():
                return False
            
            # 启动语音会话
            if await self.voice_client.start_session(self.session_config):
                self.logger.info("语音会话启动成功")
                
                # 启动消息接收任务
                self.receive_task = asyncio.create_task(self.voice_client.receive_messages())
                
                # 启动音频设备
                self.output_stream = self.audio_device.open_output_stream()
                self.logger.info("音频输出流已打开")
                
                # 启动音频处理线程
                self.is_running = True
                self.is_playing = True
                
                # 启动播放线程
                self.player_thread = threading.Thread(target=self._audio_player_loop)
                self.player_thread.daemon = True
                self.player_thread.start()
                
                # 只有在真实音频设备可用时才启动录音线程
                if PYAUDIO_AVAILABLE:
                    self.is_recording = True
                    self.recorder_thread = threading.Thread(target=self._audio_recorder_loop)
                    self.recorder_thread.daemon = True
                    self.recorder_thread.start()
                else:
                    self.logger.info("PyAudio不可用，跳过音频录制")
            
            self.logger.info("集成语音会话启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"启动语音会话失败: {e}")
            return False
    
    async def stop(self):
        """停止语音会话，此方法为非阻塞设计，会立即返回"""
        try:
            self.logger.info("开始执行非阻塞式停止语音会话流程...")
            
            # 1. 立即设置状态标志，通知所有内部循环线程停止
            self.is_running = False
            self.is_recording = False
            self.is_playing = False
            
            # 2. 优先、异步地关闭网络连接
            try:
                if self.voice_client and self.voice_client.is_connected:
                    self.logger.info("正在异步断开WebSocket连接...")
                    # 创建一个任务来执行断开，不直接等待
                    asyncio.create_task(self.voice_client.disconnect())
                    self.logger.info("WebSocket断开任务已提交")
            except Exception as e:
                self.logger.error(f"提交WebSocket断开任务时出错: {e}", exc_info=True)
                
            # 3. 将所有阻塞的清理操作提交到后台线程执行，且不等待其完成
            def _blocking_cleanup_task():
                """包含所有阻塞操作的清理函数"""
                self.logger.info("后台清理线程：开始执行...")
                try:
                    # 清理PyAudio设备资源，这是一个阻塞操作
                    self.audio_device.cleanup()
                    self.logger.info("后台清理线程：音频设备已成功清理。")
                except Exception as e:
                    self.logger.error(f"后台清理线程：清理音频设备时出错: {e}", exc_info=True)
                self.logger.info("后台清理线程：任务执行完毕。")

            try:
                loop = asyncio.get_running_loop()
                loop.run_in_executor(None, _blocking_cleanup_task)
                self.logger.info("阻塞的设备清理任务已成功提交到后台线程。")
            except RuntimeError:
                self.logger.warning("无法获取事件循环，将在当前线程同步执行清理任务...")
                _blocking_cleanup_task()

            self.logger.info("非阻塞式停止流程已完成，函数将立即返回。")
            return True
            
        except Exception as e:
            self.logger.error(f"执行停止语音会话流程时发生严重错误: {e}", exc_info=True)
            return False
    
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
        """音频录制线程"""
        input_stream = None
        
        try:
            # 等待会话完全启动
            time.sleep(0.5)
            
            # 打开音频输入流
            input_stream = self.audio_device.open_input_stream()
            self.logger.info("音频输入流已打开")
            
            while self.is_recording and self.is_running:
                try:
                    if PYAUDIO_AVAILABLE and input_stream:
                        # 检查会话状态 - 使用更可靠的状态检查
                        if not self.voice_client or not self.voice_client.is_connected:
                            self.logger.debug("语音服务未连接，跳过音频发送")
                            time.sleep(0.2)
                            continue
                    
                    # 读取音频数据
                    audio_data = input_stream.read(
                        self.audio_device.input_config.chunk,
                        exception_on_overflow=False
                    )
                    
                    # 发送到语音服务 - 使用保存的事件循环引用
                    if self.main_loop and not self.main_loop.is_closed():
                        future = asyncio.run_coroutine_threadsafe(
                            self.voice_client.send_audio(audio_data),
                            self.main_loop
                        )
                        # 不等待结果，避免阻塞
                        try:
                            future.result(timeout=0.1)  # 短暂超时
                        except concurrent.futures.TimeoutError:
                            # 超时是正常的，继续录音
                            pass
                        except Exception as e:
                            self.logger.warning(f"发送音频数据失败: {e}")
                    else:
                        self.logger.warning("主事件循环不可用，跳过音频发送")
                except Exception as e:
                    self.logger.error(f"音频录制错误: {e}")
                    time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"音频录制错误: {e}")
        
        self.logger.info("音频录制线程已停止")
    
    async def _handle_voice_message(self, message: VoiceMessage):
        """处理语音服务消息"""
        try:
            if message.message_type == 'SERVER_FULL_RESPONSE':
                if message.payload_msg:
                    # 检查是否有文本结果
                    if isinstance(message.payload_msg, dict) and 'result' in message.payload_msg:
                        result = message.payload_msg['result']
                        if result and self.on_text_received_callback:
                            self.on_text_received_callback(result)
                    
                    # 检查是否有音频数据
                    if isinstance(message.payload_msg, dict) and 'audio' in message.payload_msg:
                        audio_data = message.payload_msg['audio']
                        if audio_data and self.on_audio_received_callback:
                            # 音频数据可能是base64编码的字符串
                            if isinstance(audio_data, str):
                                import base64
                                try:
                                    audio_data = base64.b64decode(audio_data)
                                except Exception as e:
                                    self.logger.error(f"解码音频数据失败: {e}")
                                    return
                            
                            self.on_audio_received_callback(audio_data)
                            # 添加到播放队列
                            self.audio_queue.put(audio_data)
                    
                    # 处理纯音频响应（ACK类型）
                    elif isinstance(message.payload_msg, bytes):
                        # 直接是音频数据
                        self.audio_queue.put(message.payload_msg)
                        if self.on_audio_received_callback:
                            self.on_audio_received_callback(message.payload_msg)
                            
            elif message.message_type == 'SERVER_ACK':
                # SERVER_ACK 通常包含音频数据
                if isinstance(message.payload_msg, bytes):
                    self.audio_queue.put(message.payload_msg)
                    if self.on_audio_received_callback:
                        self.on_audio_received_callback(message.payload_msg)
                        
            elif message.message_type == 'SERVER_ERROR':
                self.logger.error(f"服务器错误: {message.payload_msg}")
                
                # 检查是否是会话重建错误
                if (isinstance(message.payload_msg, dict) and 
                    'error' in message.payload_msg and
                    'recreate session' in str(message.payload_msg['error'])):
                    self.logger.warning("服务器要求重建会话，尝试重新连接...")
                    
                    # 标记会话需要重启
                    self.voice_client.is_session_started = False
                    
                    # 尝试重新建立会话
                    if self.main_loop and not self.main_loop.is_closed():
                        # 在主事件循环中执行重连
                        asyncio.run_coroutine_threadsafe(
                            self._recreate_session(),
                            self.main_loop
                        )
                
        except Exception as e:
            self.logger.error(f"处理语音消息失败: {e}", exc_info=True)
    
    async def _recreate_session(self):
        """重新创建会话"""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"开始重建语音会话... (尝试 {attempt + 1}/{max_retries})")
                
                # 1. 停止录音，避免继续发送音频
                self.is_recording = False
                
                # 2. 断开当前连接
                await self.voice_client.disconnect()
                
                # 3. 等待一段时间
                await asyncio.sleep(retry_delay)
                
                # 4. 创建新的客户端实例
                self.voice_client = VoiceServiceClient(
                    config=self.voice_config,
                    session_id=None  # 使用新的会话ID
                )
                self.voice_client.on_message_received = self._handle_voice_message
                
                # 5. 重新连接
                if await self.voice_client.connect():
                    # 6. 重新启动会话
                    if await self.voice_client.start_session(self.session_config):
                        self.logger.info("会话重建成功")
                        
                        # 7. 重新启动消息接收
                        asyncio.create_task(self.voice_client.receive_messages())
                        
                        # 8. 恢复录音
                        if PYAUDIO_AVAILABLE:
                            self.is_recording = True
                        
                        return True
                    else:
                        self.logger.error(f"会话重建失败：无法启动新会话 (尝试 {attempt + 1}/{max_retries})")
                else:
                    self.logger.error(f"会话重建失败：无法连接到服务器 (尝试 {attempt + 1}/{max_retries})")
                
                # 增加重试延迟
                retry_delay *= 2
                
            except Exception as e:
                self.logger.error(f"重建会话时发生错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
        
        self.logger.error(f"会话重建失败：已尝试{max_retries}次")
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取会话状态"""
        return {
            "is_running": self.is_running,
            "is_recording": self.is_recording,
            "is_playing": self.is_playing,
            "voice_client_status": self.voice_client.get_status(),
            "audio_available": PYAUDIO_AVAILABLE
        } 
"""
音频处理模块 - TTS和STT功能
"""

import asyncio
from typing import Optional, Callable, Any
import numpy as np
from pathlib import Path
import tempfile
import json
import base64
import io
import wave

# 音频处理库
try:
    import pyaudio
    import speech_recognition as sr
    from gtts import gTTS
    import pyttsx3
    import edge_tts
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("音频库未安装，TTS/STT功能将不可用")

# OpenAI兼容的TTS/STT
try:
    import httpx
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AudioHandler:
    """音频处理器基类"""
    
    def __init__(self):
        self.is_recording = False
        self.is_playing = False
    
    async def text_to_speech(self, text: str, voice: str = "default") -> bytes:
        """文本转语音"""
        raise NotImplementedError
    
    async def speech_to_text(self, audio_data: bytes) -> str:
        """语音转文本"""
        raise NotImplementedError
    
    async def play_audio(self, audio_data: bytes):
        """播放音频"""
        raise NotImplementedError
    
    async def record_audio(self, duration: Optional[float] = None) -> bytes:
        """录制音频"""
        raise NotImplementedError


class EdgeTTSHandler(AudioHandler):
    """使用Edge TTS的音频处理器"""
    
    def __init__(self):
        super().__init__()
        if not AUDIO_AVAILABLE:
            raise ImportError("需要安装edge-tts: pip install edge-tts")
        
        self.voice_map = {
            "default": "zh-CN-XiaoxiaoNeural",
            "male": "zh-CN-YunxiNeural",
            "female": "zh-CN-XiaoxiaoNeural",
            "professional": "zh-CN-YunyangNeural"
        }
    
    async def text_to_speech(self, text: str, voice: str = "default") -> bytes:
        """使用Edge TTS转换文本到语音"""
        voice_name = self.voice_map.get(voice, self.voice_map["default"])
        
        communicate = edge_tts.Communicate(text, voice_name)
        
        # 生成临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            await communicate.save(tmp_file.name)
            
            # 读取音频数据
            with open(tmp_file.name, 'rb') as f:
                audio_data = f.read()
            
            # 删除临时文件
            Path(tmp_file.name).unlink()
            
        return audio_data
    
    async def speech_to_text(self, audio_data: bytes) -> str:
        """使用speech_recognition进行语音识别"""
        if not AUDIO_AVAILABLE:
            return ""
        
        recognizer = sr.Recognizer()
        
        # 将音频数据转换为AudioData对象
        with io.BytesIO(audio_data) as audio_file:
            with sr.AudioFile(audio_file) as source:
                audio = recognizer.record(source)
        
        try:
            # 使用Google Speech Recognition
            text = recognizer.recognize_google(audio, language='zh-CN')
            return text
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"语音识别请求失败: {e}")
            return ""
    
    async def play_audio(self, audio_data: bytes):
        """播放音频数据"""
        if not AUDIO_AVAILABLE:
            return
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(audio_data)
            tmp_file_path = tmp_file.name
        
        # 使用系统默认播放器播放
        import subprocess
        import platform
        
        try:
            if platform.system() == 'Windows':
                subprocess.run(['start', '', tmp_file_path], shell=True)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['afplay', tmp_file_path])
            else:  # Linux
                subprocess.run(['xdg-open', tmp_file_path])
            
            # 等待播放完成（简单估算）
            await asyncio.sleep(3)
            
        finally:
            # 删除临时文件
            Path(tmp_file_path).unlink(missing_ok=True)
    
    async def record_audio(self, duration: Optional[float] = None) -> bytes:
        """录制音频"""
        if not AUDIO_AVAILABLE:
            return b""
        
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            
            if duration:
                audio = recognizer.record(source, duration=duration)
            else:
                # 监听直到检测到停顿
                audio = recognizer.listen(source)
        
        # 转换为WAV格式
        wav_data = audio.get_wav_data()
        return wav_data


class OpenAICompatibleHandler(AudioHandler):
    """OpenAI兼容的TTS/STT处理器"""
    
    def __init__(self, api_key: str, api_base: str = "https://api.openai.com/v1"):
        super().__init__()
        if not OPENAI_AVAILABLE:
            raise ImportError("需要安装httpx: pip install httpx")
        
        self.api_key = api_key
        self.api_base = api_base
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        self.voice_map = {
            "default": "nova",
            "male": "onyx",
            "female": "nova",
            "professional": "alloy"
        }
    
    async def text_to_speech(self, text: str, voice: str = "default") -> bytes:
        """使用OpenAI TTS API"""
        voice_name = self.voice_map.get(voice, self.voice_map["default"])
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/audio/speech",
                headers=self.headers,
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": voice_name,
                    "response_format": "mp3"
                }
            )
            
            if response.status_code == 200:
                return response.content
            else:
                raise Exception(f"TTS请求失败: {response.text}")
    
    async def speech_to_text(self, audio_data: bytes) -> str:
        """使用OpenAI STT API"""
        async with httpx.AsyncClient() as client:
            # 创建multipart表单数据
            files = {
                "file": ("audio.wav", audio_data, "audio/wav"),
                "model": (None, "whisper-1"),
                "language": (None, "zh")
            }
            
            response = await client.post(
                f"{self.api_base}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files=files
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("text", "")
            else:
                raise Exception(f"STT请求失败: {response.text}")


class LocalTTSHandler(AudioHandler):
    """本地TTS处理器（使用pyttsx3）"""
    
    def __init__(self):
        super().__init__()
        if not AUDIO_AVAILABLE:
            raise ImportError("需要安装pyttsx3: pip install pyttsx3")
        
        self.engine = pyttsx3.init()
        
        # 设置中文语音
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                self.engine.setProperty('voice', voice.id)
                break
        
        # 设置语速和音量
        self.engine.setProperty('rate', 180)
        self.engine.setProperty('volume', 0.9)
    
    async def text_to_speech(self, text: str, voice: str = "default") -> bytes:
        """使用pyttsx3转换文本到语音"""
        # pyttsx3不直接支持返回音频数据，需要保存到文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            self.engine.save_to_file(text, tmp_file.name)
            self.engine.runAndWait()
            
            # 读取音频数据
            with open(tmp_file.name, 'rb') as f:
                audio_data = f.read()
            
            # 删除临时文件
            Path(tmp_file.name).unlink()
            
        return audio_data


class AudioManager:
    """音频管理器 - 统一接口"""
    
    def __init__(self, handler_type: str = "edge", **kwargs):
        """
        初始化音频管理器
        
        Args:
            handler_type: 处理器类型 ("edge", "openai", "local")
            **kwargs: 传递给具体处理器的参数
        """
        self.handler = self._create_handler(handler_type, **kwargs)
        self.audio_callback: Optional[Callable[[bytes], Any]] = None
        self.text_callback: Optional[Callable[[str], Any]] = None
    
    def _create_handler(self, handler_type: str, **kwargs) -> AudioHandler:
        """创建音频处理器"""
        if handler_type == "edge":
            return EdgeTTSHandler()
        elif handler_type == "openai":
            api_key = kwargs.get("api_key")
            api_base = kwargs.get("api_base", "https://api.openai.com/v1")
            if not api_key:
                raise ValueError("OpenAI处理器需要提供api_key")
            return OpenAICompatibleHandler(api_key, api_base)
        elif handler_type == "local":
            return LocalTTSHandler()
        else:
            raise ValueError(f"不支持的处理器类型: {handler_type}")
    
    def set_audio_callback(self, callback: Callable[[bytes], Any]):
        """设置音频数据回调"""
        self.audio_callback = callback
    
    def set_text_callback(self, callback: Callable[[str], Any]):
        """设置文本数据回调"""
        self.text_callback = callback
    
    async def speak(self, text: str, voice: str = "default") -> bytes:
        """文本转语音并播放"""
        audio_data = await self.handler.text_to_speech(text, voice)
        
        if self.audio_callback:
            await self.audio_callback(audio_data)
        
        # 播放音频
        await self.handler.play_audio(audio_data)
        
        return audio_data
    
    async def listen(self, duration: Optional[float] = None) -> str:
        """录制音频并转文本"""
        audio_data = await self.handler.record_audio(duration)
        
        if self.audio_callback:
            await self.audio_callback(audio_data)
        
        text = await self.handler.speech_to_text(audio_data)
        
        if self.text_callback:
            await self.text_callback(text)
        
        return text
    
    async def continuous_listen(self, stop_event: asyncio.Event):
        """持续监听模式"""
        while not stop_event.is_set():
            try:
                text = await self.listen()
                if text and self.text_callback:
                    await self.text_callback(text)
            except Exception as e:
                print(f"监听错误: {e}")
                await asyncio.sleep(0.1) 
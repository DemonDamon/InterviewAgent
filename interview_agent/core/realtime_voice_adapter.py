"""
实时语音适配器 - 连接智能对话管理器与实时语音系统
"""

import asyncio
import json
from typing import Dict, Optional, Callable
from pathlib import Path
import logging

from .intelligent_dialog_manager import IntelligentDialogManager, DialogState
from .llm_client import WildcardLLMClient
from .realtime_voice_bridge import RealtimeVoiceBridge


class RealtimeVoiceAdapter:
    """实时语音适配器"""
    
    def __init__(self, 
                 dialog_manager: IntelligentDialogManager):
        self.dialog_manager = dialog_manager
        self.logger = logging.getLogger(__name__)
        
        # 运行状态
        self.is_running = False
        self.is_connected = False
        
        # 回调函数
        self.on_connection_change: Optional[Callable] = None
        self.on_audio_received: Optional[Callable] = None
        self.on_text_received: Optional[Callable] = None
        
        # 创建实时语音桥接器
        self.voice_bridge = RealtimeVoiceBridge(
            on_text_received=self._on_voice_text_received,
            on_audio_received=self._on_voice_audio_received
        )
        
        # 设置对话管理器回调
        self.dialog_manager.set_callbacks(
            on_state_change=self._on_dialog_state_change,
            on_audio_output=self._on_audio_output
        )
    
    async def start(self):
        """启动实时语音适配器"""
        try:
            self.logger.info("启动实时语音适配器")
            self.is_running = True
            
            # 初始化对话会话
            greeting = await self.dialog_manager.initialize_session()
            
            # 启动WebSocket连接
            await self._connect_websocket()
            
            # 发送开场白
            # 暂时禁用send_text，因为可能触发recreate session错误
            # TODO: 需要确认正确的TTS协议
            # await self._send_text_to_speech(greeting)
            self.logger.info(f"面试官开场白: {greeting}")
            
            # 启动音频处理循环
            await self._start_audio_processing_loop()
            
        except Exception as e:
            self.logger.error(f"启动适配器失败: {e}")
            raise
    
    async def stop(self):
        """停止实时语音适配器"""
        self.logger.info("停止实时语音适配器")
        self.is_running = False
        
        await self.voice_bridge.stop()
        self.is_connected = False
    
    async def add_supervisor_instruction(self, instruction: str):
        """添加监督员指令"""
        await self.dialog_manager.add_supervisor_instruction(instruction)
    
    async def _connect_websocket(self):
        """连接语音服务"""
        try:
            self.logger.info("连接到实时语音服务")
            success = await self.voice_bridge.start()
            
            if success:
                self.is_connected = True
                if self.on_connection_change:
                    self.on_connection_change(True)
            else:
                self.is_connected = False
                if self.on_connection_change:
                    self.on_connection_change(False)
                raise Exception("语音服务连接失败")
                
        except Exception as e:
            self.logger.error(f"语音服务连接失败: {e}")
            self.is_connected = False
            if self.on_connection_change:
                self.on_connection_change(False)
            raise
    
    async def _start_audio_processing_loop(self):
        """启动音频处理循环"""
        self.logger.info("启动音频处理循环")
        
        while self.is_running:
            try:
                # 短暂休眠避免CPU占用过高
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"音频处理循环错误: {e}")
                await asyncio.sleep(0.1)
    
    async def _on_voice_text_received(self, text: str):
        """收到语音识别文本的回调"""
        try:
            if text and text.strip():
                self.logger.info(f"识别到语音: {text}")
                
                # 发送给对话管理器处理
                response = await self.dialog_manager.process_candidate_input(text)
                
                # 将回应转换为语音
                # 暂时禁用send_text，因为可能触发recreate session错误
                # TODO: 需要确认正确的TTS协议
                # await self._send_text_to_speech(response)
                self.logger.info(f"面试官回复: {response}")
                
        except Exception as e:
            self.logger.error(f"处理语音文本失败: {e}")
    
    def _on_voice_audio_received(self, audio_data: bytes):
        """收到语音音频的回调"""
        self.logger.debug(f"收到音频数据: {len(audio_data)} bytes")
        if self.on_audio_received:
            self.on_audio_received(audio_data)
    
    async def _send_text_to_speech(self, text: str):
        """文字转语音并发送"""
        try:
            self.logger.info(f"转换文字为语音: {text[:50]}...")
            
            # 使用语音桥接器发送文本
            await self.voice_bridge.send_text(text)
            
        except Exception as e:
            self.logger.error(f"文字转语音失败: {e}")
    
    def _on_dialog_state_change(self, old_state: DialogState, new_state: DialogState):
        """对话状态变更回调"""
        self.logger.info(f"对话状态变更: {old_state.value} -> {new_state.value}")
        
        # 根据状态变更执行相应操作
        if new_state == DialogState.COMPLETED:
            # 面试结束，可以关闭连接
            asyncio.create_task(self.stop())
    
    def _on_audio_output(self, audio_data: bytes):
        """音频输出回调"""
        # 在实时语音模式下，这个回调可能不需要
        pass
    
    async def add_audio_input(self, audio_data: bytes):
        """添加音频输入"""
        await self.voice_bridge.send_audio(audio_data)
    
    def get_dialog_summary(self) -> Dict:
        """获取对话摘要"""
        return self.dialog_manager.get_conversation_summary()


class VoiceInterviewSession:
    """语音面试会话"""
    
    def __init__(self, 
                 llm_client: WildcardLLMClient,
                 interview_plan: Dict,
                 candidate_name: str = "候选人"):
        
        # 创建对话管理器
        self.dialog_manager = IntelligentDialogManager(
            llm_client=llm_client,
            interview_plan=interview_plan,
            candidate_name=candidate_name
        )
        
        # 创建语音适配器
        self.voice_adapter = RealtimeVoiceAdapter(self.dialog_manager)
        
        self.logger = logging.getLogger(__name__)
    
    async def start_interview(self) -> Dict:
        """开始语音面试"""
        try:
            self.logger.info("开始语音面试会话")
            
            # 启动语音适配器
            await self.voice_adapter.start()
            
            return {
                "status": "success",
                "message": "语音面试已开始",
                "session_info": self.voice_adapter.get_dialog_summary()
            }
            
        except Exception as e:
            self.logger.error(f"启动语音面试失败: {e}")
            return {
                "status": "error",
                "message": f"启动失败: {str(e)}"
            }
    
    async def stop_interview(self) -> Dict:
        """停止语音面试"""
        try:
            await self.voice_adapter.stop()
            
            return {
                "status": "success",
                "message": "语音面试已停止",
                "summary": self.voice_adapter.get_dialog_summary()
            }
            
        except Exception as e:
            self.logger.error(f"停止语音面试失败: {e}")
            return {
                "status": "error",
                "message": f"停止失败: {str(e)}"
            }
    
    async def add_supervisor_instruction(self, instruction: str) -> Dict:
        """添加监督员指令"""
        try:
            await self.voice_adapter.add_supervisor_instruction(instruction)
            
            return {
                "status": "success",
                "message": f"监督员指令已添加: {instruction}"
            }
            
        except Exception as e:
            self.logger.error(f"添加监督员指令失败: {e}")
            return {
                "status": "error",
                "message": f"添加指令失败: {str(e)}"
            }
    
    def get_session_status(self) -> Dict:
        """获取会话状态"""
        return {
            "is_running": self.voice_adapter.is_running,
            "is_connected": self.voice_adapter.is_connected,
            "dialog_summary": self.voice_adapter.get_dialog_summary()
        } 
    
    def get_conversation_history(self):
        """获取对话历史（Gradio格式）"""
        # 从对话管理器获取原始对话历史
        raw_history = self.dialog_manager.context.conversation_history
        
        # 转换为Gradio Chatbot格式
        gradio_history = []
        temp_user_msg = None
        
        for turn in raw_history:
            if turn["role"] == "candidate":
                # 候选人的消息在左边
                temp_user_msg = turn["content"]
            elif turn["role"] == "interviewer":
                # 面试官的消息在右边
                if temp_user_msg is not None:
                    gradio_history.append([temp_user_msg, turn["content"]])
                    temp_user_msg = None
                else:
                    gradio_history.append([None, turn["content"]])
        
        # 如果最后有未配对的用户消息
        if temp_user_msg is not None:
            gradio_history.append([temp_user_msg, None])
        
        return gradio_history 
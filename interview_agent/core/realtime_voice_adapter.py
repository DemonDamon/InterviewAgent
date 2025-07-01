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
            
            # 初始化本地对话状态，但不依赖其生成的开场白
            await self.dialog_manager.initialize_session()

            # 在建立连接前，构建包含面试计划的动态配置
            dynamic_session_config = None
            if hasattr(self.dialog_manager, 'interview_plan') and self.dialog_manager.interview_plan:
                plan = self.dialog_manager.interview_plan
                
                # 创建一个只包含核心信息的、精简版的面试规划，以减小初始上下文长度
                summary_plan = {
                    "candidate_name": plan.get("candidate_info", {}).get("name", "候选人"),
                    "position": plan.get("candidate_info", {}).get("position", "所申请岗位"),
                    "sections": [
                        {
                            "name": section.get("name"),
                            "questions": [q.get("question") for q in section.get("questions", [])]
                        } for section in plan.get("sections", [])
                    ]
                }
                plan_text = json.dumps(summary_plan, ensure_ascii=False, indent=2)
                
                # 使用 "history" 字段传递结构化上下文，以建立真正的对话式Session
                dynamic_session_config = {
                    "dialog": {
                        "history": [
                            {
                                "role": "system",
                                "content": "你是一名专业的、顶级的AI技术面试官。你的语气应该专业、友善、且有条理。严格按照用户提供的JSON计划进行面试。"
                            },
                            {
                                "role": "user",
                                "content": f"你好，请严格按照我提供的JSON格式面试计划摘要来主持这场技术面试。请首先做一个自然的开场白，然后直接提出第一个问题。这是计划摘要：\n\n```json\n{plan_text}\n```"
                            }
                        ]
                    }
                }
                self.logger.info("已构建包含精简面试计划的 'history' 配置，将在建立会话时使用。")
            else:
                self.logger.warning("在 dialog_manager 中未找到面试计划，将使用默认配置启动语音会话。")
            
            # 启动WebSocket连接，并传入包含面试计划的配置
            await self._connect_websocket(dynamic_session_config)
            
            # 启动音频处理循环
            await self._start_audio_processing_loop()
            
        except Exception as e:
            self.logger.error(f"启动适配器失败: {e}", exc_info=True)
            raise

    async def stop(self):
        """停止实时语音适配器"""
        self.logger.info("停止实时语音适配器")
        self.is_running = False
        
        try:
            # 先标记状态变更，确保其他组件不再尝试使用
            self.is_connected = False
            
            # 停止语音桥接器
            if self.voice_bridge:
                try:
                    self.logger.info("正在停止语音桥接器...")
                    await self.voice_bridge.stop()
                    self.logger.info("语音桥接器已停止")
                except Exception as e:
                    self.logger.error(f"停止语音桥接器失败: {e}", exc_info=True)
            
            self.logger.info("实时语音适配器已停止")
            return True
        except Exception as e:
            self.logger.error(f"停止实时语音适配器失败: {e}", exc_info=True)
            return False
    
    async def add_supervisor_instruction(self, instruction: str):
        """添加监督员指令"""
        await self.dialog_manager.add_supervisor_instruction(instruction)
    
    async def _connect_websocket(self, dynamic_session_config: Optional[Dict] = None):
        """连接语音服务"""
        try:
            self.logger.info("连接到实时语音服务")
            success = await self.voice_bridge.start(dynamic_session_config)
            
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
                
                # 调用本地对话管理器处理候选人输入，以更新我们的内部状态和对话历史。
                # 但它的返回值（面试官的回应）将不再被发送。
                response = await self.dialog_manager.process_candidate_input(text)
                
                # 【关键修复】: 在对话式会话中，我们不应主动发送文本进行TTS。
                # 服务器会根据其内部LLM的判断自动生成并发送语音。
                # 主动发送文本会破坏会话状态，导致连接被关闭。
                # await self._send_text_to_speech(response)
                
                self.logger.info(f"本地对话管理器生成的回复（仅用于记录，不发送）: {response}")
                
        except Exception as e:
            self.logger.error(f"处理语音文本失败: {e}", exc_info=True)
    
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
            self.logger.info("开始停止语音面试...")
            stop_result = await self.voice_adapter.stop()
            
            if stop_result:
                self.logger.info("语音面试已成功停止")
                return {
                    "status": "success",
                    "message": "语音面试已停止",
                    "summary": self.voice_adapter.get_dialog_summary()
                }
            else:
                self.logger.warning("语音面试停止过程中出现问题，但已尽可能清理资源")
                return {
                    "status": "partial_success",
                    "message": "语音面试已停止，但过程中出现问题",
                    "summary": self.voice_adapter.get_dialog_summary()
                }
            
        except Exception as e:
            self.logger.error(f"停止语音面试失败: {e}", exc_info=True)
            # 尝试强制停止适配器
            try:
                self.voice_adapter.is_running = False
                self.voice_adapter.is_connected = False
            except:
                pass
                
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
"""
语音客户端模块 - 处理与豆包语音服务的WebSocket通信
"""

import asyncio
import uuid
import logging
from typing import Dict, Any, Optional, Callable
import websockets
import websockets.exceptions

from .voice_protocol import VoiceProtocolHandler, VoiceMessage


class VoiceServiceClient:
    """语音服务客户端"""
    
    def __init__(self, 
                 config: Dict[str, Any],
                 session_id: Optional[str] = None):
        self.config = config
        self.session_id = session_id or str(uuid.uuid4())
        self.ws: Optional[websockets.WebSocketServerProtocol] = None
        self.logid = ""
        self.logger = logging.getLogger(__name__)
        
        # 回调函数
        self.on_message_received: Optional[Callable] = None
        self.on_connection_lost: Optional[Callable] = None
        
        # 连接状态
        self.is_connected = False
        self.is_session_started = False
    
    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            self.logger.info(f"连接到语音服务: {self.config['base_url']}")
            
            # websockets 13.x 使用 extra_headers 参数
            self.ws = await websockets.connect(
                self.config['base_url'],
                extra_headers=self.config['headers'],
                ping_interval=None
            )
            
            # websockets 13.x 中响应头的获取方式
            if hasattr(self.ws, 'response_headers'):
                self.logid = self.ws.response_headers.get("X-Tt-Logid", "") or ""
            else:
                self.logid = ""
            self.logger.info(f"连接成功，logid: {self.logid}")
            
            # 发送连接请求
            await self._send_connection_request()
            
            self.is_connected = True
            return True
            
        except Exception as e:
            self.logger.error(f"连接失败: {e}")
            self.is_connected = False
            return False
    
    async def start_session(self, session_config: Dict[str, Any]) -> bool:
        """启动语音会话"""
        try:
            if not self.is_connected:
                raise Exception("未连接到语音服务")
            
            self.logger.info("启动语音会话")
            
            # 发送会话启动请求
            request = VoiceProtocolHandler.create_session_request(
                self.session_id, session_config
            )
            await self.ws.send(request)
            
            # 接收响应
            response = await self.ws.recv()
            message = VoiceProtocolHandler.parse_response(response)
            
            if message.message_type == 'SERVER_FULL_RESPONSE':
                self.logger.info("会话启动成功")
                self.is_session_started = True
                return True
            else:
                self.logger.error(f"会话启动失败: {message.payload_msg}")
                return False
                
        except Exception as e:
            self.logger.error(f"启动会话失败: {e}")
            return False
    
    async def send_audio(self, audio_data: bytes):
        """发送音频数据"""
        try:
            if not self.is_connected or not self.is_session_started:
                raise Exception("会话未启动")
            
            request = VoiceProtocolHandler.create_audio_request(
                self.session_id, audio_data
            )
            await self.ws.send(request)
            
        except Exception as e:
            self.logger.error(f"发送音频失败: {e}")
            raise
    
    async def send_text(self, text: str):
        """发送文本（用于TTS）"""
        try:
            if not self.is_connected or not self.is_session_started:
                raise Exception("会话未启动")
            
            # 使用专门的TTS请求方法
            request = VoiceProtocolHandler.create_tts_request(
                self.session_id, text
            )
            await self.ws.send(request)
            
            self.logger.info(f"已发送TTS请求: {text[:50]}...")
            
        except Exception as e:
            self.logger.error(f"发送文本失败: {e}")
            raise
    
    async def receive_messages(self):
        """接收消息循环"""
        try:
            while self.is_connected and self.ws:
                try:
                    response = await self.ws.recv()
                    message = VoiceProtocolHandler.parse_response(response)
                    
                    # 调用回调函数
                    if self.on_message_received:
                        await self.on_message_received(message)
                        
                    # 检查是否是会话结束事件
                    if (message.event and 
                        message.event in [152, 153]):  # 会话结束事件
                        self.logger.info(f"收到会话结束事件: {message.event}")
                        self.is_session_started = False
                        break
                        
                except websockets.exceptions.ConnectionClosed:
                    self.logger.info("WebSocket连接已关闭")
                    self.is_connected = False
                    self.is_session_started = False
                    break
                except Exception as e:
                    self.logger.error(f"接收消息错误: {e}")
                    # 不要立即断开，可能是临时错误
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            self.logger.error(f"消息接收循环错误: {e}")
        finally:
            # 只有在真正断开连接时才更新状态
            if self.on_connection_lost:
                await self.on_connection_lost()
    
    async def finish_session(self):
        """结束会话"""
        try:
            if self.is_session_started and self.ws:
                self.logger.info("结束语音会话")
                
                request = VoiceProtocolHandler.create_finish_session_request(
                    self.session_id
                )
                await self.ws.send(request)
                self.is_session_started = False
                
        except Exception as e:
            self.logger.error(f"结束会话失败: {e}")
    
    async def disconnect(self):
        """断开连接"""
        try:
            # 先标记状态
            self.is_session_started = False
            
            if self.is_connected and self.ws:
                self.logger.info("断开语音服务连接")
                
                try:
                    # 只有在WebSocket连接正常时才发送断开请求
                    # 检查连接是否打开（兼容不同版本的websockets）
                    if hasattr(self.ws, 'state') and hasattr(self.ws.state, 'name'):
                        is_open = self.ws.state.name == 'OPEN'
                    elif hasattr(self.ws, 'open'):
                        is_open = self.ws.open
                    else:
                        # 默认尝试发送
                        is_open = True
                    
                    if is_open:
                        # 发送断开连接请求
                        request = VoiceProtocolHandler.create_finish_connection_request()
                        await self.ws.send(request)
                        
                        # 接收响应（设置短超时）
                        try:
                            response = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                            message = VoiceProtocolHandler.parse_response(response)
                            self.logger.info(f"断开连接响应: {message.payload_msg}")
                        except asyncio.TimeoutError:
                            self.logger.debug("断开连接响应超时（正常情况）")
                        except websockets.exceptions.ConnectionClosed:
                            self.logger.debug("连接已关闭")
                except Exception as e:
                    self.logger.debug(f"发送断开请求时出错（可忽略）: {e}")
                
                # 关闭WebSocket
                try:
                    await self.ws.close()
                except Exception as e:
                    self.logger.debug(f"关闭WebSocket时出错（可忽略）: {e}")
                
        except Exception as e:
            self.logger.error(f"断开连接失败: {e}")
        finally:
            # 确保状态被重置
            self.is_connected = False
            self.is_session_started = False
            self.ws = None
            self.logger.info("连接已断开")
    
    async def _send_connection_request(self):
        """发送连接请求"""
        request = VoiceProtocolHandler.create_connection_request()
        await self.ws.send(request)
        
        # 接收响应
        response = await self.ws.recv()
        message = VoiceProtocolHandler.parse_response(response)
        
        if message.message_type != 'SERVER_FULL_RESPONSE':
            raise Exception(f"连接请求失败: {message.payload_msg}")
        
        self.logger.info("连接请求成功")
    
    def get_status(self) -> Dict[str, Any]:
        """获取客户端状态"""
        return {
            "is_connected": self.is_connected,
            "is_session_started": self.is_session_started,
            "session_id": self.session_id,
            "logid": self.logid
        } 
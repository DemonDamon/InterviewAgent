"""
语音协议处理模块 - 处理豆包语音服务的通信协议
"""

import gzip
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

# 协议版本和头部配置
PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

# 消息类型
CLIENT_FULL_REQUEST = 0b0001
CLIENT_AUDIO_ONLY_REQUEST = 0b0010
SERVER_FULL_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111

# 消息类型特定标志
NO_SEQUENCE = 0b0000
POS_SEQUENCE = 0b0001
NEG_SEQUENCE = 0b0010
NEG_SEQUENCE_1 = 0b0011
MSG_WITH_EVENT = 0b0100

# 序列化方法
NO_SERIALIZATION = 0b0000
JSON = 0b0001
THRIFT = 0b0011
CUSTOM_TYPE = 0b1111

# 压缩类型
NO_COMPRESSION = 0b0000
GZIP = 0b0001
CUSTOM_COMPRESSION = 0b1111


@dataclass
class VoiceMessage:
    """语音消息数据类"""
    message_type: str
    payload_msg: Any = None
    session_id: str = ""
    event: Optional[int] = None
    seq: Optional[int] = None
    code: Optional[int] = None
    payload_size: int = 0


class VoiceProtocolHandler:
    """语音协议处理器"""
    
    @staticmethod
    def generate_header(
        version: int = PROTOCOL_VERSION,
        message_type: int = CLIENT_FULL_REQUEST,
        message_type_specific_flags: int = MSG_WITH_EVENT,
        serial_method: int = JSON,
        compression_type: int = GZIP,
        reserved_data: int = 0x00,
        extension_header: bytes = bytes()
    ) -> bytearray:
        """生成协议头部"""
        header = bytearray()
        header_size = int(len(extension_header) / 4) + 1
        header.append((version << 4) | header_size)
        header.append((message_type << 4) | message_type_specific_flags)
        header.append((serial_method << 4) | compression_type)
        header.append(reserved_data)
        header.extend(extension_header)
        return header
    
    @staticmethod
    def parse_response(response_data: bytes) -> VoiceMessage:
        """解析服务器响应"""
        if isinstance(response_data, str):
            return VoiceMessage(message_type="UNKNOWN")
        
        # 解析头部
        protocol_version = response_data[0] >> 4
        header_size = response_data[0] & 0x0f
        message_type = response_data[1] >> 4
        message_type_specific_flags = response_data[1] & 0x0f
        serialization_method = response_data[2] >> 4
        message_compression = response_data[2] & 0x0f
        reserved = response_data[3]
        header_extensions = response_data[4:header_size * 4]
        payload = response_data[header_size * 4:]
        
        # 创建消息对象
        message = VoiceMessage(message_type="UNKNOWN")
        payload_msg = None
        payload_size = 0
        start = 0
        
        if message_type == SERVER_FULL_RESPONSE or message_type == SERVER_ACK:
            message.message_type = 'SERVER_FULL_RESPONSE'
            if message_type == SERVER_ACK:
                message.message_type = 'SERVER_ACK'
                
            if message_type_specific_flags & NEG_SEQUENCE > 0:
                message.seq = int.from_bytes(payload[:4], "big", signed=False)
                start += 4
                
            if message_type_specific_flags & MSG_WITH_EVENT > 0:
                message.event = int.from_bytes(payload[:4], "big", signed=False)
                start += 4
                
            payload = payload[start:]
            session_id_size = int.from_bytes(payload[:4], "big", signed=True)
            session_id = payload[4:session_id_size]
            message.session_id = str(session_id)
            payload = payload[4 + session_id_size:]
            payload_size = int.from_bytes(payload[:4], "big", signed=False)
            payload_msg = payload[4:]
            
        elif message_type == SERVER_ERROR_RESPONSE:
            message.message_type = 'SERVER_ERROR'
            message.code = int.from_bytes(payload[:4], "big", signed=False)
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            payload_msg = payload[8:]
        
        if payload_msg is not None:
            # 解压缩
            if message_compression == GZIP:
                payload_msg = gzip.decompress(payload_msg)
            
            # 反序列化
            if serialization_method == JSON:
                payload_msg = json.loads(str(payload_msg, "utf-8"))
            elif serialization_method != NO_SERIALIZATION:
                payload_msg = str(payload_msg, "utf-8")
            
            message.payload_msg = payload_msg
            message.payload_size = payload_size
        
        return message
    
    @staticmethod
    def create_connection_request() -> bytearray:
        """创建连接请求"""
        request = bytearray(VoiceProtocolHandler.generate_header())
        request.extend(int(1).to_bytes(4, 'big'))
        payload_bytes = str.encode("{}")
        payload_bytes = gzip.compress(payload_bytes)
        request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        request.extend(payload_bytes)
        return request
    
    @staticmethod
    def create_session_request(session_id: str, config: Dict[str, Any]) -> bytearray:
        """创建会话请求"""
        payload_bytes = str.encode(json.dumps(config))
        payload_bytes = gzip.compress(payload_bytes)
        request = bytearray(VoiceProtocolHandler.generate_header())
        request.extend(int(100).to_bytes(4, 'big'))
        request.extend((len(session_id)).to_bytes(4, 'big'))
        request.extend(str.encode(session_id))
        request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        request.extend(payload_bytes)
        return request
    
    @staticmethod
    def create_audio_request(session_id: str, audio_data: bytes) -> bytearray:
        """创建音频请求"""
        request = bytearray(
            VoiceProtocolHandler.generate_header(
                message_type=CLIENT_AUDIO_ONLY_REQUEST,
                serial_method=NO_SERIALIZATION
            )
        )
        request.extend(int(200).to_bytes(4, 'big'))
        request.extend((len(session_id)).to_bytes(4, 'big'))
        request.extend(str.encode(session_id))
        payload_bytes = gzip.compress(audio_data)
        request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        request.extend(payload_bytes)
        return request
    
    @staticmethod
    def create_finish_session_request(session_id: str) -> bytearray:
        """创建结束会话请求"""
        request = bytearray(VoiceProtocolHandler.generate_header())
        request.extend(int(102).to_bytes(4, 'big'))
        payload_bytes = str.encode("{}")
        payload_bytes = gzip.compress(payload_bytes)
        request.extend((len(session_id)).to_bytes(4, 'big'))
        request.extend(str.encode(session_id))
        request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        request.extend(payload_bytes)
        return request
    
    @staticmethod
    def create_finish_connection_request() -> bytearray:
        """创建结束连接请求"""
        request = bytearray(VoiceProtocolHandler.generate_header())
        request.extend(int(2).to_bytes(4, 'big'))
        payload_bytes = str.encode("{}")
        payload_bytes = gzip.compress(payload_bytes)
        request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        request.extend(payload_bytes)
        return request 
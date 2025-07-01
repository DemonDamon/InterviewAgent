# 语音服务集成架构

## 概述

我们已经将原来的 `realtime_dialog` 厂商demo代码完全集成到 `interview_agent` 系统中，实现了深度整合的实时语音面试功能。

## 新架构

### 核心模块

1. **`voice_protocol.py`** - 语音协议处理
   - `VoiceProtocolHandler`: 处理豆包语音服务的通信协议
   - `VoiceMessage`: 语音消息数据类
   - 完全替代原 `realtime_dialog/protocol.py`

2. **`voice_client.py`** - 语音服务客户端
   - `VoiceServiceClient`: WebSocket客户端，连接豆包语音服务
   - 完全替代原 `realtime_dialog/realtime_dialog_client.py`

3. **`voice_audio_manager.py`** - 音频管理
   - `AudioDeviceManager`: 音频设备管理
   - `IntegratedVoiceSession`: 集成语音会话管理器
   - 完全替代原 `realtime_dialog/audio_manager.py` 的功能

4. **`realtime_voice_bridge.py`** - 语音桥接器（已更新）
   - 使用集成的语音模块，不再依赖外部 `realtime_dialog`
   - 直接从 `config.settings` 读取配置

5. **`intelligent_dialog_manager.py`** - 智能对话管理
   - 基于面试流程的智能对话状态机
   - 支持监督员实时干预

6. **`realtime_voice_adapter.py`** - 语音适配器
   - 连接智能对话管理器与语音系统
   - 提供统一的语音面试接口

### 配置集成

语音服务配置已集成到 `config/settings.py` 中：

```python
# 火山引擎语音服务配置
volc_app_id: str = Field("", env="VOLC_APP_ID")
volc_access_key: str = Field("", env="VOLC_ACCESS_KEY") 
volc_resource_id: str = Field("volc.speech.dialog", env="VOLC_RESOURCE_ID")
volc_app_key: str = Field("PlgvMymc7f3tQnJ6", env="VOLC_APP_KEY")
```

## 使用方法

### 1. 环境配置

在 `.env` 文件中添加：

```bash
# 火山引擎语音服务配置
VOLC_APP_ID=your_app_id
VOLC_ACCESS_KEY=your_access_key
VOLC_RESOURCE_ID=volc.speech.dialog
VOLC_APP_KEY=PlgvMymc7f3tQnJ6
```

### 2. 启动语音面试

```python
from interview_agent.core.realtime_voice_adapter import VoiceInterviewSession
from interview_agent.core.llm_client import WildcardLLMClient

# 创建LLM客户端
llm_client = WildcardLLMClient()

# 创建语音面试会话
voice_session = VoiceInterviewSession(
    llm_client=llm_client,
    interview_plan=interview_plan,
    candidate_name="张三"
)

# 启动面试
result = await voice_session.start_interview()

# 添加监督员指令
await voice_session.add_supervisor_instruction("请深入询问Python经验")

# 停止面试
await voice_session.stop_interview()
```

### 3. 在ExecutorAgent中使用

```python
# 在面试控制面板中选择"使用实时语音模式（豆包）"
executor = ExecutorAgent(llm_client, use_realtime_voice=True)
result = await executor.conduct_interview(
    interview_plan=plan,
    candidate_name="张三"
)
```

## 优势

1. **完全集成**: 不再依赖外部 `realtime_dialog` 目录
2. **统一配置**: 语音服务配置集成到主配置系统
3. **智能对话**: 基于面试流程的智能状态管理
4. **监督员干预**: 支持实时指令和动态调整
5. **模块化设计**: 清晰的模块分离和接口定义
6. **错误处理**: 完善的异常处理和日志记录
7. **兼容性**: 支持pyaudio不可用时的模拟模式

## 移除旧代码

现在可以安全地删除 `realtime_dialog/` 目录，因为所有功能都已集成到 `interview_agent/core/` 中。

## 依赖

- `websockets>=12.0` - WebSocket通信
- `pyaudio` - 音频处理（可选，不可用时使用模拟模式）
- `python-dotenv` - 环境变量管理

## 故障排除

1. **pyaudio安装问题**: 系统会自动使用模拟模式
2. **语音服务连接失败**: 检查网络和API配置
3. **权限问题**: 确保麦克风访问权限
4. **配置错误**: 验证 `.env` 文件中的API密钥 
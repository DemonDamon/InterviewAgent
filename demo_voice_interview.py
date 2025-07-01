"""
实时语音面试演示
"""

import asyncio
import logging
from config.settings import settings
from interview_agent.core.realtime_voice_bridge import RealtimeVoiceBridge

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class VoiceInterviewDemo:
    """语音面试演示类"""
    
    def __init__(self):
        self.voice_bridge = None
        self.conversation_history = []
        
    def on_text_received(self, text: str):
        """处理接收到的文本"""
        print(f"\n候选人说: {text}")
        self.conversation_history.append(f"候选人: {text}")
        
        # 这里可以调用面试智能体来生成回复
        # 现在我们只是简单回复
        asyncio.create_task(self.respond_to_candidate(text))
    
    def on_audio_received(self, audio_data: bytes):
        """处理接收到的音频"""
        # 音频会自动播放，这里只是记录
        pass
    
    async def respond_to_candidate(self, candidate_text: str):
        """回复候选人"""
        # 简单的回复逻辑
        if "你好" in candidate_text or "您好" in candidate_text:
            response = "你好！欢迎参加今天的面试。请先简单介绍一下自己。"
        elif "介绍" in candidate_text and "自己" in candidate_text:
            response = "谢谢你的介绍。能说说你最近做的一个项目吗？"
        elif "项目" in candidate_text:
            response = "听起来很有意思。在这个项目中，你遇到的最大挑战是什么？"
        else:
            response = "好的，我明白了。还有其他想补充的吗？"
        
        print(f"面试官说: {response}")
        self.conversation_history.append(f"面试官: {response}")
        
        # 发送语音回复
        # 暂时禁用send_text，因为可能触发recreate session错误
        # TODO: 需要确认正确的TTS协议
        # if self.voice_bridge:
        #     await self.voice_bridge.send_text(response)
    
    async def start_interview(self):
        """开始面试"""
        try:
            print("=== 实时语音面试演示 ===")
            print("正在启动语音服务...")
            
            # 创建语音桥接器
            self.voice_bridge = RealtimeVoiceBridge(
                on_text_received=self.on_text_received,
                on_audio_received=self.on_audio_received
            )
            
            # 启动语音服务
            if await self.voice_bridge.start():
                print("[OK] 语音服务启动成功！")
                print("\n面试开始，请开始说话...")
                print("(按 Ctrl+C 结束面试)")
                
                # 发送欢迎语
                welcome_text = "你好，欢迎参加今天的面试。我是你的面试官，请问你准备好了吗？"
                # 暂时禁用send_text
                # await self.voice_bridge.send_text(welcome_text)
                print(f"\n面试官说: {welcome_text}")
                
                # 保持运行
                while True:
                    await asyncio.sleep(1)
                    
            else:
                print("[ERROR] 语音服务启动失败")
                
        except KeyboardInterrupt:
            print("\n\n面试结束")
        except Exception as e:
            print(f"[ERROR] 发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 停止语音服务
            if self.voice_bridge:
                await self.voice_bridge.stop()
            
            # 打印对话历史
            print("\n=== 对话记录 ===")
            for line in self.conversation_history:
                print(line)

async def main():
    """主函数"""
    demo = VoiceInterviewDemo()
    await demo.start_interview()

if __name__ == "__main__":
    asyncio.run(main()) 
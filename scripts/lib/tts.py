"""
共享 TTS 工具库
edge-tts 异步包装（含重试）。
"""
import asyncio
import edge_tts


async def tts_one(text, output_path, voice="zh-CN-YunxiNeural", max_retries=3):
    """合成单条 TTS 语音（含重试）

    Args:
        text: 文本内容
        output_path: 输出音频路径（.mp3）
        voice: edge-tts 语音名称
        max_retries: 最大重试次数
    """
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"    TTS 重试 {attempt + 1}/{max_retries}: {e}")
                await asyncio.sleep(2)
            else:
                raise

"""全局配置"""
import os
from datetime import datetime, timedelta

# === 路径 ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = datetime.now().strftime("%Y-%m-%d")
OUTPUT_DIR = os.path.join(BASE_DIR, TODAY)
DATA_DIR = os.path.join(OUTPUT_DIR, "data")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
CLIPS_DIR = os.path.join(OUTPUT_DIR, "clips")
FINAL_DIR = os.path.join(OUTPUT_DIR, "final")
SUBTITLES_DIR = os.path.join(OUTPUT_DIR, "subtitles")

# === 视频参数 ===
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
CLIP_DURATION = 60  # 每段 60 秒

# === 转场特效 ===
FADE_DURATION = 1.0

# === TTS 配音 ===
TTS_VOICE = "zh-CN-XiaoxiaoNeural"

# === 字体 ===
FONT_CN = "/System/Library/Fonts/STHeiti Medium.ttc"  # 中文黑体
FONT_EN = "/System/Library/Fonts/Helvetica.ttc"        # 英文
FONT_CN_PINGFANG = "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/3419f2a427639ad8c8e139149a287865a90fa17e.asset/AssetData/PingFang.ttc"

# === GitHub ===
GITHUB_TRENDING_URL = "https://github.com/trending"
GITHUB_API = "https://api.github.com"
TOP_N = 10

def ensure_dirs():
    """创建所有输出目录"""
    for d in [DATA_DIR, IMAGES_DIR, AUDIO_DIR, SUBTITLES_DIR, CLIPS_DIR, FINAL_DIR]:
        os.makedirs(d, exist_ok=True)
    return OUTPUT_DIR

if __name__ == "__main__":
    out = ensure_dirs()
    print(f"输出目录: {out}")
    print(f"日期: {TODAY}")

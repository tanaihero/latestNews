"""头条热榜功能配置 — 独立于 config.py / config_douyin.py"""
import os
from datetime import datetime

# === 路径 ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = datetime.now().strftime("%Y-%m-%d")
TOUTIAO_SUFFIX = "toutiao"
OUTPUT_DIR = os.path.join(BASE_DIR, f"{TODAY}{TOUTIAO_SUFFIX}")
DATA_DIR = os.path.join(OUTPUT_DIR, "data")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
SUBTITLES_DIR = os.path.join(OUTPUT_DIR, "subtitles")
CLIPS_DIR = os.path.join(OUTPUT_DIR, "clips")
FINAL_DIR = os.path.join(OUTPUT_DIR, "final")

# === 视频参数（与其他平台一致） ===
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

# === 字体 ===
FONT_CN = "/System/Library/Fonts/STHeiti Medium.ttc"
FONT_EN = "/System/Library/Fonts/Helvetica.ttc"
FONT_CN_PINGFANG = "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/3419f2a427639ad8c8e139149a287865a90fa17e.asset/AssetData/PingFang.ttc"

# === 头条 API（三级容错） ===
TOUTIAO_API_PRIMARY = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
TOUTIAO_API_FALLBACK = "https://v2.xxapi.cn/api/toutiaohot"
TOUTIAO_API_FALLBACK2 = "https://uapis.cn/api/v1/misc/hotboard?type=toutiao"

TOP_N = 10

# === TTS 配音 ===
# YunxiNeural：男声新闻播报风（与抖音活泼女声形成差异）
TTS_VOICE = "zh-CN-YunxiNeural"

# === 转场特效 ===
FADE_DURATION = 1.0

# === 配音控制（精简约20秒/条） ===
NARRATION_CHARS_PER_ITEM = 100   # 每条 ~100 字，约 20 秒
NARRATION_INTRO_CHARS = 120      # 开场白 ~120 字


def ensure_dirs():
    """创建所有输出目录"""
    for d in [DATA_DIR, IMAGES_DIR, AUDIO_DIR, SUBTITLES_DIR, CLIPS_DIR, FINAL_DIR]:
        os.makedirs(d, exist_ok=True)
    return OUTPUT_DIR


if __name__ == "__main__":
    out = ensure_dirs()
    print(f"头条热榜输出目录: {out}")
    print(f"日期: {TODAY}")

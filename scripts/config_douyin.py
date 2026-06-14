"""抖音热搜功能配置 — 独立于原 config.py，互不影响"""
import os
from datetime import datetime

# === 路径 ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = datetime.now().strftime("%Y-%m-%d")
DOUYIN_SUFFIX = "douyin"
OUTPUT_DIR = os.path.join(BASE_DIR, f"{TODAY}{DOUYIN_SUFFIX}")
DATA_DIR = os.path.join(OUTPUT_DIR, "data")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
SUBTITLES_DIR = os.path.join(OUTPUT_DIR, "subtitles")
CLIPS_DIR = os.path.join(OUTPUT_DIR, "clips")
FINAL_DIR = os.path.join(OUTPUT_DIR, "final")

# === 视频参数（与 GitHub 一致） ===
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

# === 字体（复用） ===
FONT_CN = "/System/Library/Fonts/STHeiti Medium.ttc"
FONT_EN = "/System/Library/Fonts/Helvetica.ttc"
FONT_CN_PINGFANG = "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/3419f2a427639ad8c8e139149a287865a90fa17e.asset/AssetData/PingFang.ttc"

# === 抖音热搜 API ===
# 主 API：抖音官方端点
DOUYIN_API_PRIMARY = "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/"
# 备用 API：第三方聚合（数据更丰富）
DOUYIN_API_FALLBACK = "https://v2.xxapi.cn/api/douyinhot"
# 第二个备用
DOUYIN_API_FALLBACK2 = "https://uapis.cn/api/v1/misc/hotboard?type=douyin"

TOP_N = 10

# === TTS 配音 ===
# XiaoyiNeural：年轻活泼女声，最接近二次元风格（XiaoxuanNeural 不可用，XiaoyiNeural 为最佳替代）
TTS_VOICE = "zh-CN-XiaoyiNeural"

# === 转场特效 ===
FADE_DURATION = 1.0  # 淡入淡出时长（秒）


def ensure_dirs():
    """创建所有输出目录"""
    for d in [DATA_DIR, IMAGES_DIR, AUDIO_DIR, SUBTITLES_DIR, CLIPS_DIR, FINAL_DIR]:
        os.makedirs(d, exist_ok=True)
    return OUTPUT_DIR


if __name__ == "__main__":
    out = ensure_dirs()
    print(f"抖音热搜输出目录: {out}")
    print(f"日期: {TODAY}")

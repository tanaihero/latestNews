"""
Phase 11: 头条热榜 TTS 配音生成（精简版 ~20秒/条）
Edge TTS — YunxiNeural 男声新闻播报风
复用 lib/tts.py + lib/subtitles.py
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_toutiao import (
    ensure_dirs, DATA_DIR, AUDIO_DIR, SUBTITLES_DIR,
    TTS_VOICE, TODAY, NARRATION_CHARS_PER_ITEM
)
from lib.tts import tts_one
from lib.subtitles import generate_srt
from lib.video import get_audio_duration
from lib.drawing import format_hot_value


LABEL_MAP = {1: "新", 2: "热", 3: "沸", 4: "爆"}


def generate_intro(items):
    """精简开场白 ~120 字"""
    max_hot = items[0]["hot_value"] if items else 0
    min_hot = items[-1]["hot_value"] if items else 0

    lines = [
        f"大家好，欢迎收看头条热榜速递！",
        f"今天是{TODAY}，来看今天最热的10个话题。",
        f"第一名热度高达{format_hot_value(max_hot)}，",
        f"最后一名也有{format_hot_value(min_hot)}。",
        f"我们直接开始！",
    ]
    return "".join(lines)


def generate_narration(item, all_items):
    """为单条热搜生成精简解说 (~100字, ~20秒)"""
    rank = item["rank"]
    word = item["word"]
    hot = item["hot_value"]
    hot_text = format_hot_value(hot)
    video_count = item.get("video_count", 0)
    label = LABEL_MAP.get(item.get("label", 0), "")

    lines = []

    # 1. 引入
    lines.append(f"第{rank}名，{word}。")

    # 2. 数据
    try:
        vc = int(video_count) if video_count else 0
    except (ValueError, TypeError):
        vc = 0
    if vc > 0:
        lines.append(f"热度{hot_text}，已有{vc}个相关讨论。")
    else:
        lines.append(f"热度{hot_text}。")
    if label:
        lines.append(f"标记为{label}。")

    # 3. 简评（按排名分3档）
    if rank <= 3:
        lines.append(f"作为今天前三热点，这个话题引发了全民级别的关注，讨论量呈爆发式增长。")
    elif rank <= 7:
        lines.append(f"这个话题最近热度持续攀升，很多博主在跟进讨论，建议去了解一下。")
    else:
        lines.append(f"虽然排名靠后，但上升势头明显，很多后来爆火的话题都从这里起步。")

    # 4. 过渡
    if rank < len(all_items):
        lines.append("继续看下一条。")
    else:
        lines.append("以上就是今天头条热榜的全部内容，感谢收看，我们明天见！")

    return "".join(lines)


def main():
    ensure_dirs()

    data_path = os.path.join(DATA_DIR, "toutiao_hot.json")
    with open(data_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"[Phase 11] 为 {len(items)} 条热榜生成精简配音 ({TTS_VOICE})...")

    narrations = []

    # 0. 开场白
    intro_text = generate_intro(items)
    intro_path = os.path.join(AUDIO_DIR, "narration_00_intro.mp3")
    narrations.append({"rank": 0, "text": intro_text, "type": "intro"})
    print(f"  开场白 ({len(intro_text)}字)...")
    asyncio.run(tts_one(intro_text, intro_path, voice=TTS_VOICE))
    print(f"  已保存: {intro_path}")
    dur = get_audio_duration(intro_path)
    srt_path = os.path.join(SUBTITLES_DIR, "sub_00_intro.srt")
    generate_srt(intro_text, dur, srt_path)

    # 1-10 每条热搜
    for item in items:
        rank = item["rank"]
        narration = generate_narration(item, items)
        narrations.append({"rank": rank, "text": narration, "type": "hot"})

        output_path = os.path.join(AUDIO_DIR, f"narration_{rank:02d}.mp3")
        print(f"  第{rank}名「{item['word'][:8]}」({len(narration)}字)...")
        asyncio.run(tts_one(narration, output_path, voice=TTS_VOICE))
        print(f"  已保存: {output_path}")
        dur = get_audio_duration(output_path)
        srt_path = os.path.join(SUBTITLES_DIR, f"sub_{rank:02d}.srt")
        generate_srt(narration, dur, srt_path)

    # 保存文案
    narrations_path = os.path.join(DATA_DIR, "narrations.json")
    with open(narrations_path, "w", encoding="utf-8") as f:
        json.dump(narrations, f, ensure_ascii=False, indent=2)

    print(f"[Phase 11] 完成! (配音 + 字幕)")


if __name__ == "__main__":
    main()

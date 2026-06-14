"""
Phase 3: 生成配音音频 + SRT 字幕 (Edge TTS + 字幕生成)
每个项目生成两段配音：
  Part 1 (配合 Page 1 概览卡片): 项目名、作者、语言、星标、fork 等基本信息
  Part 2 (配合 Page 2 README 摘要): 中文摘要详述、标签、开源协议、CTA
复用 lib/tts.py (含重试) + lib/subtitles.py + lib/video.py
"""
import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    ensure_dirs, DATA_DIR, AUDIO_DIR, SUBTITLES_DIR, TTS_VOICE
)
from lib.tts import tts_one
from lib.subtitles import generate_srt
from lib.video import get_audio_duration


def clean_html(text):
    """去除 HTML 标签"""
    return re.sub(r"<[^>]+>", "", text).strip()


def format_stars(count):
    """格式化星数（中文口语）"""
    if count >= 10000:
        return f"{count / 10000:.1f}万"
    if count >= 1000:
        return f"{count // 1000}千{count % 1000}" if count % 1000 else f"{count // 1000}千"
    return str(count)


# ─── 开场白 ─────────────────────────────────────────────────

def generate_intro(repos):
    """封面开场白"""
    total_stars = sum(r["stars"] for r in repos)
    top = repos[0]
    lines = [
        "大家好！欢迎收看本期 GitHub 热门项目 Top 10 周报。",
        f"本期榜单涵盖了从 AI 编程助手、安全工具、到前端框架等多个方向的热门项目。",
        f"十个项目合计收获了超过 {format_stars(total_stars)} 颗星标，竞争非常激烈。",
        f"其中最亮眼的是 {top['name']}，短短几天就拿下了 {format_stars(top['stars'])} 颗星，堪称现象级项目。",
        "话不多说，让我们一起看看这些项目都有什么亮点吧！",
    ]
    return "".join(lines)


# ─── 每个项目的两段配音 ─────────────────────────────────────

OPENERS = [
    "来看看本周的冠军项目！",
    "第二名来啦，这个项目同样值得关注。",
    "第三名，季军选手登场。",
    "第四名来了，实力不容小觑。",
    "第五名，刚好卡在半程线上。",
    "后半程开始！第六名是这个。",
    "第七名，让我们继续。",
    "第八名，低调但有实力。",
    "第九名，快到尾声了。",
    "最后压轴的第十名！",
]


def generate_narration_part1(repo):
    """Part 1: 项目概览配音（配合 Page 1 卡片）"""
    rank = repo["rank"]
    name = repo["name"]
    owner = repo["owner"]
    stars = repo["stars"]
    forks = repo["forks"]
    lang = repo.get("language") or "多语言"
    desc = repo.get("description", "") or ""

    opener = OPENERS[(rank - 1) % len(OPENERS)]

    lines = [f"第{rank}名。{opener}"]
    lines.append(f"项目叫 {name}，作者是 {owner}，主要用 {lang} 编写。")
    lines.append(f"目前在 GitHub 上已经拿到了 {format_stars(stars)} 颗星标，还有 {format_stars(forks)} 个 fork。")

    # 简单描述（如果有中文描述就用中文，英文就跳过让 part2 详细说）
    if desc and desc != "暂无描述":
        # 判断是否中文
        ascii_ratio = sum(1 for c in desc if ord(c) < 128) / max(len(desc), 1)
        if ascii_ratio < 0.5:
            # 中文描述，直接读
            lines.append(f"它的功能是：{desc}")
        else:
            lines.append("接下来让我们看看这个项目的详细介绍。")
    else:
        lines.append("接下来让我们看看这个项目的详细介绍。")

    return "".join(lines)


def generate_narration_part2(repo):
    """Part 2: README 中文摘要配音（配合 Page 2 卡片）"""
    name = repo["name"]
    owner = repo["owner"]

    # 使用 Phase 2 预生成的中文朗读文本
    summary_data = repo.get("readme_summary_cn", {})
    narration_text = ""
    if isinstance(summary_data, dict):
        narration_text = summary_data.get("narration_text", "")
    elif isinstance(summary_data, str):
        narration_text = summary_data

    if narration_text:
        return narration_text + f"感兴趣的朋友可以去 GitHub 搜索 {owner}/{name}，记得给个 star 哦。"
    else:
        return f"该项目暂无详细的文档介绍。感兴趣的朋友可以去 GitHub 搜索 {owner}/{name}，记得给个 star 哦。"


# ─── Main ────────────────────────────────────────────────────

def main():
    ensure_dirs()

    data_path = os.path.join(DATA_DIR, "repos.json")
    with open(data_path, "r", encoding="utf-8") as f:
        repos = json.load(f)

    print(f"[Phase 3] 为 {len(repos)} 个项目生成双段配音 ({TTS_VOICE})...")

    narrations = []

    # 0. 封面开场白
    intro_text = generate_intro(repos)
    intro_path = os.path.join(AUDIO_DIR, "narration_00_intro.mp3")
    narrations.append({"rank": 0, "text": intro_text, "type": "intro"})
    print(f"  开场白 ({len(intro_text)}字)...")
    asyncio.run(tts_one(intro_text, intro_path, voice=TTS_VOICE))
    print(f"  已保存: {intro_path}")
    # 生成字幕
    dur = get_audio_duration(intro_path)
    srt_path = os.path.join(SUBTITLES_DIR, "sub_00_intro.srt")
    generate_srt(intro_text, dur, srt_path)

    # 1-10 每个项目：生成两段配音
    for repo in repos:
        rank = repo["rank"]

        # --- Part 1: 概览 ---
        text_p1 = generate_narration_part1(repo)
        path_p1 = os.path.join(AUDIO_DIR, f"narration_{rank:02d}_p1.mp3")
        print(f"  第{rank}名 Part1 ({len(text_p1)}字)...")
        asyncio.run(tts_one(text_p1, path_p1, voice=TTS_VOICE))
        dur_p1 = get_audio_duration(path_p1)
        srt_p1 = os.path.join(SUBTITLES_DIR, f"sub_{rank:02d}_p1.srt")
        generate_srt(text_p1, dur_p1, srt_p1)

        # --- Part 2: README 摘要 ---
        text_p2 = generate_narration_part2(repo)
        path_p2 = os.path.join(AUDIO_DIR, f"narration_{rank:02d}_p2.mp3")
        print(f"  第{rank}名 Part2 ({len(text_p2)}字)...")
        asyncio.run(tts_one(text_p2, path_p2, voice=TTS_VOICE))
        dur_p2 = get_audio_duration(path_p2)
        srt_p2 = os.path.join(SUBTITLES_DIR, f"sub_{rank:02d}_p2.srt")
        generate_srt(text_p2, dur_p2, srt_p2)

        narrations.append({
            "rank": rank,
            "text_part1": text_p1,
            "text_part2": text_p2,
            "type": "repo",
        })

        print(f"  第{rank}名完成: P1={dur_p1:.1f}s, P2={dur_p2:.1f}s")

    # 保存文案
    narrations_path = os.path.join(DATA_DIR, "narrations.json")
    with open(narrations_path, "w", encoding="utf-8") as f:
        json.dump(narrations, f, ensure_ascii=False, indent=2)

    print(f"[Phase 3] 完成! (双段配音 + 字幕)")


if __name__ == "__main__":
    main()

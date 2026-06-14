"""
Phase 4: GitHub 视频合成（双页卡片 + 转场 + 大字幕）
每个项目生成 2 个视频片段（Page1 概览 + Page2 README 摘要），合并为完整合集视频。
复用 lib/video.py + lib/subtitles.py 共享工具。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    ensure_dirs, DATA_DIR, IMAGES_DIR, AUDIO_DIR, SUBTITLES_DIR,
    CLIPS_DIR, FINAL_DIR, VIDEO_WIDTH, VIDEO_HEIGHT,
    VIDEO_FPS, TODAY, FADE_DURATION, FONT_CN_PINGFANG
)
from lib.video import make_clip_with_transition, concatenate_clips
from lib.subtitles import build_drawtext_filters


def drawtext_filters_for_github(srt_path):
    """GitHub 专用 drawtext 滤镜构建 — 字号 36，位置偏下 h*0.82"""
    return build_drawtext_filters(srt_path, FONT_CN_PINGFANG, fontsize=36, y_expr="h*0.82")


def main():
    ensure_dirs()

    data_path = os.path.join(DATA_DIR, "repos.json")
    with open(data_path, "r", encoding="utf-8") as f:
        repos = json.load(f)

    print(f"[Phase 4] 合成 GitHub 双页视频（含转场 + drawtext 字幕，转场 {FADE_DURATION}s）...")

    all_clips = []

    # 0. 封面片段（用开场白音频 + 字幕）
    thumbnail_img = os.path.join(IMAGES_DIR, "thumbnail.png")
    intro_audio = os.path.join(AUDIO_DIR, "narration_00_intro.mp3")
    intro_srt = os.path.join(SUBTITLES_DIR, "sub_00_intro.srt")
    thumbnail_clip = os.path.join(CLIPS_DIR, "clip_00_thumbnail.mp4")
    if os.path.exists(thumbnail_img) and os.path.exists(intro_audio):
        if make_clip_with_transition(
            thumbnail_img, intro_audio, thumbnail_clip,
            video_width=VIDEO_WIDTH, video_height=VIDEO_HEIGHT, video_fps=VIDEO_FPS,
            fade_duration=FADE_DURATION,
            srt_path=intro_srt,
            drawtext_filters_func=drawtext_filters_for_github,
            label="封面"
        ):
            all_clips.append(thumbnail_clip)

    # 1-10 每个项目：生成 2 个片段（Page1 + Page2）
    for repo in repos:
        rank = repo["rank"]

        # --- Page 1: 概览 ---
        img_p1 = os.path.join(IMAGES_DIR, f"repo_{rank:02d}_p1.png")
        audio_p1 = os.path.join(AUDIO_DIR, f"narration_{rank:02d}_p1.mp3")
        srt_p1 = os.path.join(SUBTITLES_DIR, f"sub_{rank:02d}_p1.srt")
        clip_p1 = os.path.join(CLIPS_DIR, f"clip_{rank:02d}_p1.mp4")

        if os.path.exists(img_p1) and os.path.exists(audio_p1):
            if make_clip_with_transition(
                img_p1, audio_p1, clip_p1,
                video_width=VIDEO_WIDTH, video_height=VIDEO_HEIGHT, video_fps=VIDEO_FPS,
                fade_duration=FADE_DURATION,
                srt_path=srt_p1,
                drawtext_filters_func=drawtext_filters_for_github,
                label=f"第{rank}名-概览「{repo['name'][:10]}」"
            ):
                all_clips.append(clip_p1)

        # --- Page 2: README 摘要 ---
        img_p2 = os.path.join(IMAGES_DIR, f"repo_{rank:02d}_p2.png")
        audio_p2 = os.path.join(AUDIO_DIR, f"narration_{rank:02d}_p2.mp3")
        srt_p2 = os.path.join(SUBTITLES_DIR, f"sub_{rank:02d}_p2.srt")
        clip_p2 = os.path.join(CLIPS_DIR, f"clip_{rank:02d}_p2.mp4")

        if os.path.exists(img_p2) and os.path.exists(audio_p2):
            if make_clip_with_transition(
                img_p2, audio_p2, clip_p2,
                video_width=VIDEO_WIDTH, video_height=VIDEO_HEIGHT, video_fps=VIDEO_FPS,
                fade_duration=FADE_DURATION,
                srt_path=srt_p2,
                drawtext_filters_func=drawtext_filters_for_github,
                label=f"第{rank}名-详情「{repo['name'][:10]}」"
            ):
                all_clips.append(clip_p2)

    # 合并所有片段
    if all_clips:
        final_path = os.path.join(FINAL_DIR, f"github_top10_{TODAY}.mp4")
        concatenate_clips(all_clips, final_path)
        print(f"[Phase 4] 完成! 共 {len(all_clips)} 个片段")
    else:
        print("[Phase 4] 没有可合并的片段!")


if __name__ == "__main__":
    main()

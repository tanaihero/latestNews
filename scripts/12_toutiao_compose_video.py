"""
Phase 12: 头条热榜视频合成（带转场 + drawtext 字幕）
复用 lib/video.py + lib/subtitles.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_toutiao import (
    ensure_dirs, DATA_DIR, IMAGES_DIR, AUDIO_DIR, SUBTITLES_DIR,
    CLIPS_DIR, FINAL_DIR, VIDEO_WIDTH, VIDEO_HEIGHT,
    VIDEO_FPS, TODAY, FADE_DURATION, TOUTIAO_SUFFIX, FONT_CN_PINGFANG
)
from lib.video import make_clip_with_transition, concatenate_clips
from lib.subtitles import build_drawtext_filters


def drawtext_filters_for_toutiao(srt_path):
    """头条专用的 drawtext 滤镜构建（使用 PingFang 字体）"""
    return build_drawtext_filters(srt_path, FONT_CN_PINGFANG, fontsize=28, y_expr="h*0.70")


def main():
    ensure_dirs()

    data_path = os.path.join(DATA_DIR, "toutiao_hot.json")
    with open(data_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"[Phase 12] 合成头条视频（含转场 + drawtext 字幕，转场时长 {FADE_DURATION}s）...")

    all_clips = []

    # 0. 封面片段
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
            drawtext_filters_func=drawtext_filters_for_toutiao,
            label="封面"
        ):
            all_clips.append(thumbnail_clip)

    # 1-10 每条热搜
    for item in items:
        rank = item["rank"]
        image_path = os.path.join(IMAGES_DIR, f"hot_{rank:02d}.png")
        audio_path = os.path.join(AUDIO_DIR, f"narration_{rank:02d}.mp3")
        srt_path = os.path.join(SUBTITLES_DIR, f"sub_{rank:02d}.srt")
        clip_path = os.path.join(CLIPS_DIR, f"clip_{rank:02d}.mp4")

        if not os.path.exists(audio_path) or not os.path.exists(image_path):
            print(f"  跳过第{rank}名：文件不存在")
            continue

        if make_clip_with_transition(
            image_path, audio_path, clip_path,
            video_width=VIDEO_WIDTH, video_height=VIDEO_HEIGHT, video_fps=VIDEO_FPS,
            fade_duration=FADE_DURATION,
            srt_path=srt_path,
            drawtext_filters_func=drawtext_filters_for_toutiao,
            label=f"第{rank}名「{item['word'][:8]}」"
        ):
            all_clips.append(clip_path)

    # 合并
    if all_clips:
        final_path = os.path.join(FINAL_DIR, f"toutiao_hot_top10_{TODAY}.mp4")
        concatenate_clips(all_clips, final_path)
        print(f"[Phase 12] 完成!")
    else:
        print("[Phase 12] 没有可合并的片段!")


if __name__ == "__main__":
    main()

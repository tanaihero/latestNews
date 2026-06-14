"""
Phase 8: 抖音热搜视频合成（带转场特效 + 字幕）
图片+音频 → 短视频片段（含淡入淡出转场 + drawtext 字幕） → 合并为合集视频

字幕方案：使用 drawtext 滤镜替代 subtitles 滤镜（后者与 -loop 1 不兼容），
解析 SRT 文件后为每条字幕生成带时间控制的 drawtext 滤镜链。
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_douyin import (
    ensure_dirs, DATA_DIR, IMAGES_DIR, AUDIO_DIR, SUBTITLES_DIR,
    CLIPS_DIR, FINAL_DIR, VIDEO_WIDTH, VIDEO_HEIGHT,
    VIDEO_FPS, TODAY, FADE_DURATION, DOUYIN_SUFFIX, FONT_CN_PINGFANG
)


def get_audio_duration(audio_path):
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 30.0


def parse_srt_time(time_str):
    """SRT 时间戳 'HH:MM:SS,mmm' → 秒数 float"""
    m = re.match(r"(\d+):(\d+):(\d+),(\d+)", time_str.strip())
    if not m:
        return 0.0
    h, mi, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    return h * 3600 + mi * 60 + s + ms / 1000.0


def parse_srt(srt_path):
    """解析 SRT 文件，返回 [{start, end, text}, ...]"""
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    segments = []
    blocks = re.split(r"\n\n+", content)
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        # lines[0] = index, lines[1] = time range, lines[2:] = text
        time_match = re.match(r"(.+?)\s*-->\s*(.+)", lines[1])
        if not time_match:
            continue
        start = parse_srt_time(time_match.group(1))
        end = parse_srt_time(time_match.group(2))
        text = " ".join(lines[2:])
        segments.append({"start": start, "end": end, "text": text})
    return segments


def escape_drawtext(text):
    """转义 drawtext 滤镜中的特殊字符"""
    # drawtext 需要转义的字符: \ ' : % 和换行
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\u2019")  # 替换为右单引号
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    return text


def build_drawtext_filters(srt_path):
    """从 SRT 文件构建 drawtext 滤镜链"""
    segments = parse_srt(srt_path)
    if not segments:
        return ""

    font_path = FONT_CN_PINGFANG
    if not os.path.exists(font_path):
        print(f"    警告: 字体文件不存在 {font_path}")
        return ""

    # 转义字体路径中的特殊字符
    escaped_font = font_path.replace(":", "\\:").replace("'", "\\'")

    filters = []
    for seg in segments:
        text = escape_drawtext(seg["text"])
        start = seg["start"]
        end = seg["end"]

        # drawtext 参数
        dt = (
            f"drawtext=fontfile='{escaped_font}'"
            f":text='{text}'"
            f":fontsize=28"
            f":fontcolor=white"
            f":borderw=2"
            f":bordercolor=black"
            f":x=(w-text_w)/2"
            f":y=h*0.70"
            f":enable='between(t,{start:.3f},{end:.3f})'"
        )
        filters.append(dt)

    return ",".join(filters)


def make_clip_with_transition(image_path, audio_path, output_path, srt_path=None, label=""):
    """图片 + 音频 → 单个视频片段（含淡入淡出转场 + drawtext 字幕）"""
    duration = get_audio_duration(audio_path)
    total_dur = duration + 2.0  # 前后各留 1 秒缓冲

    # 视频滤镜：缩放 + 填充 + 帧率
    vf = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"fps={VIDEO_FPS}"
    )

    # 烧录字幕（使用 drawtext 替代 subtitles 滤镜）
    if srt_path and os.path.exists(srt_path):
        drawtext_filters = build_drawtext_filters(srt_path)
        if drawtext_filters:
            vf += f",{drawtext_filters}"

    # 淡入淡出转场
    vf += (
        f",fade=t=in:st=0:d={FADE_DURATION},"
        f"fade=t=out:st={total_dur - FADE_DURATION:.2f}:d={FADE_DURATION}"
    )

    # 音频滤镜：淡入淡出
    af = (
        f"afade=t=in:st=0:d={FADE_DURATION},"
        f"afade=t=out:st={total_dur - FADE_DURATION:.2f}:d={FADE_DURATION}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-c:v", "h264_videotoolbox", "-q:v", "50",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-vf", vf,
        "-af", af,
        "-t", f"{total_dur:.2f}",
        "-shortest",
        output_path
    ]
    print(f"  合成{label} ({duration:.1f}s, 含 {FADE_DURATION}s 转场)...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    失败: {result.stderr[-500:]}")
        return False
    else:
        print(f"    已保存: {output_path}")
        return True


def concatenate_clips(clip_paths, output_path):
    """用 filter_complex concat 合并所有片段"""
    n = len(clip_paths)
    cmd = ["ffmpeg", "-y"]
    for p in clip_paths:
        cmd += ["-i", p]

    # 构建 filter_complex
    parts = []
    for i in range(n):
        parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[{i}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]")
    concat_in = "".join(f"[v{i}][a{i}]" for i in range(n))
    parts.append(f"{concat_in}concat=n={n}:v=1:a=1[outv][outa]")

    cmd += [
        "-filter_complex", ";".join(parts),
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "h264_videotoolbox", "-q:v", "50",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path
    ]
    print(f"  合并 {n} 个片段中...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  合并失败，尝试分批合并...")
        mid = n // 2
        part1_path = output_path.replace(".mp4", "_part1.mp4")
        part2_path = output_path.replace(".mp4", "_part2.mp4")
        concatenate_clips(clip_paths[:mid], part1_path)
        concatenate_clips(clip_paths[mid:], part2_path)
        cmd2 = ["ffmpeg", "-y", "-i", part1_path, "-i", part2_path,
                "-filter_complex",
                "[0:v]setpts=PTS-STARTPTS[v0];[0:a]asetpts=PTS-STARTPTS[a0];[1:v]setpts=PTS-STARTPTS[v1];[1:a]asetpts=PTS-STARTPTS[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]",
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", "h264_videotoolbox", "-q:v", "50",
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", output_path]
        subprocess.run(cmd2, capture_output=True, text=True)
        for f in [part1_path, part2_path]:
            if os.path.exists(f):
                os.remove(f)
    print(f"  最终视频已保存: {output_path}")


def main():
    ensure_dirs()

    data_path = os.path.join(DATA_DIR, "douyin_hot.json")
    with open(data_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"[Phase 8] 合成抖音视频（含转场 + drawtext 字幕，转场时长 {FADE_DURATION}s）...")

    all_clips = []

    # 0. 封面片段（用开场白音频 + 字幕）
    thumbnail_img = os.path.join(IMAGES_DIR, "thumbnail.png")
    intro_audio = os.path.join(AUDIO_DIR, "narration_00_intro.mp3")
    intro_srt = os.path.join(SUBTITLES_DIR, "sub_00_intro.srt")
    thumbnail_clip = os.path.join(CLIPS_DIR, "clip_00_thumbnail.mp4")
    if os.path.exists(thumbnail_img) and os.path.exists(intro_audio):
        if make_clip_with_transition(thumbnail_img, intro_audio, thumbnail_clip,
                                     srt_path=intro_srt, label="封面"):
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

        if make_clip_with_transition(image_path, audio_path, clip_path,
                                     srt_path=srt_path,
                                     label=f"第{rank}名「{item['word'][:8]}」"):
            all_clips.append(clip_path)

    # 合并
    if all_clips:
        final_path = os.path.join(FINAL_DIR, f"douyin_hot_top10_{TODAY}.mp4")
        concatenate_clips(all_clips, final_path)
        print(f"[Phase 8] 完成!")
    else:
        print("[Phase 8] 没有可合并的片段!")


if __name__ == "__main__":
    main()

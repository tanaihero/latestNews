"""
共享视频合成工具库
ffmpeg 片段合成、转场、拼接。
从抖音视频合成脚本提取。
"""
import os
import subprocess


def get_audio_duration(audio_path):
    """用 ffprobe 获取音频时长"""
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 30.0


def make_clip_with_transition(image_path, audio_path, output_path,
                               video_width=1080, video_height=1920, video_fps=30,
                               fade_duration=1.0, srt_path=None,
                               drawtext_filters_func=None, label="",
                               encoder="h264_videotoolbox", quality=50):
    """图片 + 音频 -> 单个视频片段（含淡入淡出转场 + 可选 drawtext 字幕）

    Args:
        image_path: 图片路径
        audio_path: 音频路径
        output_path: 输出视频路径
        video_width/height/fps: 视频尺寸和帧率
        fade_duration: 转场时长（秒）
        srt_path: SRT 字幕文件路径（可选）
        drawtext_filters_func: 构建 drawtext 滤镜的函数，签名 (srt_path) -> str
        label: 日志标签
        encoder: 视频编码器
        quality: 编码器质量
    """
    duration = get_audio_duration(audio_path)
    total_dur = duration + 2.0

    vf = (
        f"scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,"
        f"pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black,"
        f"fps={video_fps}"
    )

    if srt_path and os.path.exists(srt_path) and drawtext_filters_func:
        drawtext_filters = drawtext_filters_func(srt_path)
        if drawtext_filters:
            vf += f",{drawtext_filters}"

    vf += (
        f",fade=t=in:st=0:d={fade_duration},"
        f"fade=t=out:st={total_dur - fade_duration:.2f}:d={fade_duration}"
    )

    af = (
        f"afade=t=in:st=0:d={fade_duration},"
        f"afade=t=out:st={total_dur - fade_duration:.2f}:d={fade_duration}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-c:v", encoder, "-q:v", str(quality),
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-vf", vf,
        "-af", af,
        "-t", f"{total_dur:.2f}",
        "-shortest",
        output_path
    ]
    print(f"  合成{label} ({duration:.1f}s, 含 {fade_duration}s 转场)...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    失败: {result.stderr[-500:]}")
        return False
    else:
        print(f"    已保存: {output_path}")
        return True


def concatenate_clips(clip_paths, output_path,
                      encoder="h264_videotoolbox", quality=50):
    """用 filter_complex concat 合并所有片段"""
    n = len(clip_paths)
    cmd = ["ffmpeg", "-y"]
    for p in clip_paths:
        cmd += ["-i", p]

    parts = []
    for i in range(n):
        parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[{i}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]")
    concat_in = "".join(f"[v{i}][a{i}]" for i in range(n))
    parts.append(f"{concat_in}concat=n={n}:v=1:a=1[outv][outa]")

    cmd += [
        "-filter_complex", ";".join(parts),
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", encoder, "-q:v", str(quality),
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
        concatenate_clips(clip_paths[:mid], part1_path, encoder, quality)
        concatenate_clips(clip_paths[mid:], part2_path, encoder, quality)
        cmd2 = ["ffmpeg", "-y", "-i", part1_path, "-i", part2_path,
                "-filter_complex",
                "[0:v]setpts=PTS-STARTPTS[v0];[0:a]asetpts=PTS-STARTPTS[a0];[1:v]setpts=PTS-STARTPTS[v1];[1:a]asetpts=PTS-STARTPTS[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]",
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", encoder, "-q:v", str(quality),
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", output_path]
        subprocess.run(cmd2, capture_output=True, text=True)
        for f in [part1_path, part2_path]:
            if os.path.exists(f):
                os.remove(f)
    print(f"  最终视频已保存: {output_path}")

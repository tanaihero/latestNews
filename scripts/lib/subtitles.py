"""
共享字幕工具库
SRT 生成/解析、drawtext 滤镜链构建。
从抖音 TTS + 视频合成脚本提取。
"""
import os
import re


def split_text_to_segments(text, max_chars=18):
    """将中文文本按标点分割成字幕段落，每段不超过 max_chars 字符"""
    sentences = re.split(r'([。！？；])', text)
    segments = []
    current = ""
    for part in sentences:
        if not part:
            continue
        if re.match(r'^[。！？；]$', part):
            current += part
            segments.append(current)
            current = ""
            continue
        test = current + part
        if len(test) <= max_chars:
            current = test
        else:
            if current:
                segments.append(current)
            if len(part) > max_chars:
                sub_parts = re.split(r'([，、：])', part)
                current = ""
                for sp in sub_parts:
                    if not sp:
                        continue
                    test2 = current + sp
                    if len(test2) <= max_chars:
                        current = test2
                    else:
                        if current:
                            segments.append(current)
                        current = sp
            else:
                current = part

    if current:
        segments.append(current)

    segments = [s.strip() for s in segments if s.strip()]
    return segments


def format_srt_time(seconds):
    """将秒数格式化为 SRT 时间戳 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(text, total_duration, output_path, max_chars=18):
    """根据文本和总时长生成 SRT 字幕文件"""
    segments = split_text_to_segments(text, max_chars)
    if not segments:
        return

    total_chars = sum(len(s) for s in segments)
    buffer_start = 0.5
    buffer_end = 0.5
    usable_duration = total_duration - buffer_start - buffer_end

    srt_lines = []
    current_time = buffer_start
    for i, seg in enumerate(segments):
        char_ratio = len(seg) / total_chars
        seg_duration = usable_duration * char_ratio
        seg_duration = max(0.8, min(5.0, seg_duration))

        start_time = current_time
        end_time = current_time + seg_duration
        if end_time > total_duration - 0.3:
            end_time = total_duration - 0.3

        srt_lines.append(f"{i + 1}")
        srt_lines.append(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}")
        srt_lines.append(seg)
        srt_lines.append("")

        current_time = end_time + 0.15

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))


def parse_srt_time(time_str):
    """SRT 时间戳 'HH:MM:SS,mmm' -> 秒数 float"""
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
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\u2019")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    return text


def build_drawtext_filters(srt_path, font_path, fontsize=28, y_expr="h*0.70"):
    """从 SRT 文件构建 drawtext 滤镜链

    Args:
        srt_path: SRT 文件路径
        font_path: 字体文件路径（PingFang.ttc 等）
        fontsize: 字号，默认 28
        y_expr: y 位置表达式，默认 h*0.70（底部 30%）
    """
    segments = parse_srt(srt_path)
    if not segments:
        return ""

    if not os.path.exists(font_path):
        print(f"    警告: 字体文件不存在 {font_path}")
        return ""

    escaped_font = font_path.replace(":", "\\:").replace("'", "\\'")

    filters = []
    for seg in segments:
        text = escape_drawtext(seg["text"])
        start = seg["start"]
        end = seg["end"]

        dt = (
            f"drawtext=fontfile='{escaped_font}'"
            f":text='{text}'"
            f":fontsize={fontsize}"
            f":fontcolor=white"
            f":borderw=2"
            f":bordercolor=black"
            f":x=(w-text_w)/2"
            f":y={y_expr}"
            f":enable='between(t,{start:.3f},{end:.3f})'"
        )
        filters.append(dt)

    return ",".join(filters)

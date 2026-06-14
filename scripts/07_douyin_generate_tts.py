"""
Phase 7: 抖音热搜配音生成 v2 (Edge TTS — XiaoyiNeural 年轻活泼女声)
更丰富的文案：多段落、多角度讨论、更强的互动感
"""
import asyncio
import json
import os
import sys

import edge_tts

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_douyin import ensure_dirs, DATA_DIR, AUDIO_DIR, SUBTITLES_DIR, TTS_VOICE

import re
import subprocess


def format_hot_value(count):
    if count >= 100000000:
        return f"{count / 100000000:.1f}亿"
    if count >= 10000:
        return f"{count / 10000:.0f}万"
    if count >= 1000:
        return f"{count // 1000}千"
    return str(count)


def split_text_to_segments(text, max_chars=18):
    """将中文文本按标点分割成字幕段落，每段不超过 max_chars 字符"""
    # 按句子级标点分割
    sentences = re.split(r'([。！？；])', text)
    segments = []
    current = ""
    for part in sentences:
        if not part:
            continue
        # 如果是标点，合并到当前段
        if re.match(r'^[。！？；]$', part):
            current += part
            if len(current) <= max_chars:
                segments.append(current)
                current = ""
            else:
                segments.append(current)
                current = ""
            continue
        # 检查合并后是否超长
        test = current + part
        if len(test) <= max_chars:
            current = test
        else:
            # 先提交当前
            if current:
                segments.append(current)
            # 如果单句也超长，按逗号/顿号继续切
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

    # 过滤空段
    segments = [s.strip() for s in segments if s.strip()]
    return segments


def format_srt_time(seconds):
    """将秒数格式化为 SRT 时间戳 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(text, total_duration, output_path):
    """根据文本和总时长生成 SRT 字幕文件"""
    segments = split_text_to_segments(text)
    if not segments:
        return

    # 按字符数比例分配时间
    total_chars = sum(len(s) for s in segments)
    # 留首尾各 0.5 秒缓冲
    buffer_start = 0.5
    buffer_end = 0.5
    usable_duration = total_duration - buffer_start - buffer_end

    srt_lines = []
    current_time = buffer_start
    for i, seg in enumerate(segments):
        # 按字符数占比分配时间
        char_ratio = len(seg) / total_chars
        seg_duration = usable_duration * char_ratio
        # 最短 0.8 秒，最长 5 秒
        seg_duration = max(0.8, min(5.0, seg_duration))

        start_time = current_time
        end_time = current_time + seg_duration
        # 不超过总时长
        if end_time > total_duration - 0.3:
            end_time = total_duration - 0.3

        srt_lines.append(f"{i + 1}")
        srt_lines.append(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}")
        srt_lines.append(seg)
        srt_lines.append("")

        current_time = end_time + 0.15  # 段间间隔

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))


def format_ass_time(seconds):
    """将秒数格式化为 ASS 时间戳 H:MM:SS.CC"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_ass(text, total_duration, output_path):
    """根据文本和总时长生成 ASS 字幕文件（含嵌入式样式）"""
    segments = split_text_to_segments(text)
    if not segments:
        return

    # ASS 头部 + 样式定义
    ass_header = """[Script Info]
Title: Douyin Hot Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,STHeiti,26,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2.5,1,2,30,30,576,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # 按字符数比例分配时间（与 SRT 相同逻辑）
    total_chars = sum(len(s) for s in segments)
    buffer_start = 0.5
    buffer_end = 0.5
    usable_duration = total_duration - buffer_start - buffer_end

    events = []
    current_time = buffer_start
    for seg in segments:
        char_ratio = len(seg) / total_chars
        seg_duration = usable_duration * char_ratio
        seg_duration = max(0.8, min(5.0, seg_duration))

        start_time = current_time
        end_time = current_time + seg_duration
        if end_time > total_duration - 0.3:
            end_time = total_duration - 0.3

        events.append(f"Dialogue: 0,{format_ass_time(start_time)},{format_ass_time(end_time)},Default,,0,0,0,,{seg}")
        current_time = end_time + 0.15

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        f.write("\n".join(events))
        f.write("\n")


def get_audio_duration(audio_path):
    """用 ffprobe 获取音频时长"""
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 30.0


def generate_intro(items):
    """封面开场白 — 总结全局、制造悬念"""
    total_hot = sum(i["hot_value"] for i in items)
    top = items[0]
    second = items[1] if len(items) > 1 else None
    last = items[-1] if items else None

    lines = [
        "哈喽大家好！欢迎来到今天的抖音热搜速递！",
        f"今天是{TODAY}，让我们一起来看看今天抖音上最火的话题都有哪些。",
        f"本期热搜榜单涵盖了体育、社会、娱乐、生活等多个领域，可以说是相当丰富。",
        f"十条热搜合计热度超过 {format_hot_value(total_hot)}，全网讨论量堪称爆炸级别。",
    ]

    if top:
        lines.append(
            f"其中热度最高的话题是「{top['word']}」，"
            f"热度指数高达 {format_hot_value(top['hot_value'])}，到底是什么引发了全网关注呢？"
        )
    if second:
        lines.append(
            f"紧随其后的是「{second['word']}」，热度也达到了 {format_hot_value(second['hot_value'])}。"
        )
    if last:
        lines.append(
            f"即便是排在第十位的「{last['word']}」，热度也有 {format_hot_value(last['hot_value'])}，"
            "可见今天的热点话题有多炸裂。"
        )

    lines.append(
        "好了，话不多说！让我们从第一名开始，逐条为你解读今天的热搜！"
        "看完记得点赞关注哦，我们下期再见！"
    )
    return "".join(lines)


def generate_narration(item, all_items):
    """为单条热搜生成丰富的多段解说文案"""
    rank = item["rank"]
    word = item["word"]
    hot = item["hot_value"]
    hot_text = format_hot_value(hot)
    label = item.get("label", 0)
    video_count = item.get("video_count", 0)

    label_map = {1: "新上榜", 2: "被推荐", 3: "正在热"}
    label_text = label_map.get(label, "")

    # 排名开场白（抖音风格，活泼 + 悬念感）
    openers = [
        "来啦来啦！第一名登场！今天最炸裂的热搜就是它！",
        "第二名来了！这个话题在抖音上已经是刷屏级别的讨论了。",
        "第三名！季军选手同样精彩，全网都在热议。",
        "第四名来了！虽然没进前三但讨论度依然爆表。",
        "第五名！刚好卡在半程线上，来看看是什么话题。",
        "下半场开始！第六名的话题最近势头非常猛。",
        "第七名！让我们继续往下探索。",
        "第八名！虽然排名不算靠前但话题性一点不输。",
        "第九名！马上就到最后了，这一条也很有意思。",
        "最后压轴的第十名来了！千万别小看它！",
    ]
    opener = openers[(rank - 1) % len(openers)]

    # 构建多段落文案
    lines = []

    # 段落 1: 开场 + 话题引入
    lines.append(f"第{rank}名。{opener}")
    lines.append(f"今天的热搜话题是「{word}」。")

    # 段落 2: 数据展示
    lines.append(f"先来看看数据：它的热度指数高达 {hot_text}。")
    if label_text:
        lines.append(f"同时被标记为{label_text}话题，说明关注度正在快速变化中。")
    if video_count and video_count > 0:
        lines.append(f"抖音上已经有 {video_count} 个相关视频在传播，讨论氛围非常热烈。")

    # 段落 3: 话题分析（根据排名生成不同深度）
    if rank <= 3:
        lines.append(
            f"作为今天的前三热搜，「{word}」可以说引发了全民级别的关注。"
            "打开抖音搜索这个话题，你会发现评论区已经炸锅了，"
            "各路网友纷纷发表自己的看法，讨论量呈爆发式增长。"
        )
        lines.append(
            "这种级别的热搜通常意味着事件本身具有极强的话题性和传播力，"
            "不管是正面的还是引发争议的，都实实在在地抓住了大家的注意力。"
        )
    elif rank <= 6:
        lines.append(
            f"「{word}」这个话题最近的热度一直在攀升，"
            "很多博主和自媒体都在跟进报道和讨论。"
            "从评论区来看，网友们对这个话题的看法也是五花八门，"
            "有人表示支持，有人提出质疑，讨论非常活跃。"
        )
        lines.append(
            "如果你还没关注这个话题的话，强烈建议去抖音搜一搜，"
            "了解一下事情的来龙去脉，可能还会有意想不到的收获。"
        )
    elif rank <= 9:
        lines.append(
            f"虽然「{word}」目前排在第{rank}位，"
            "但它的上升势头非常明显，随时有可能冲进前五甚至前三。"
            "这类话题往往正在发酵中，越早关注越能把握热点的第一手信息。"
        )
        lines.append(
            "而且从过往经验来看，很多后来爆火的话题，"
            "在最开始的时候都是从热搜榜的中后段起步的，"
            "所以千万不要小看任何一条热搜的潜力。"
        )
    else:
        lines.append(
            f"「{word}」作为今天的压轴话题出现在第十位，"
            "但千万不要因为排名靠后就忽视它。"
            "很多全网爆火的事件在最初上榜时都排在类似的位置，"
            "随着讨论量增加才逐渐冲到前列。"
        )
        lines.append(
            "这条热搜的热度也在持续攀升中，"
            "建议大家趁早去了解一下，说不定明天它就会成为全网焦点。"
        )

    # 段落 4: 互动引导
    if rank <= 3:
        lines.append(
            "各位朋友你们怎么看这件事呢？欢迎在评论区留下你的看法！"
            "觉得内容不错的话记得点个赞加个关注，我们每天都会带来最新的热搜解读！"
        )
    elif rank <= 6:
        lines.append(
            "对这个话题有什么想法的宝子们，评论区见！"
            "也别忘了关注我们，每天第一时间带你看抖音最热话题！"
        )
    else:
        lines.append(
            "感兴趣的朋友赶紧去抖音搜索看看吧！"
            "喜欢这期内容的话点个赞加关注，明天同一时间我们不见不散！"
        )

    # 段落 5: 过渡（非最后一条时）
    if rank < len(all_items):
        lines.append("好了，让我们继续看下一条热搜！")
    else:
        lines.append(
            "好了，以上就是今天抖音热搜 Top 10 的全部内容了。"
            "感谢大家的收看，我们明天见！拜拜！"
        )

    return "".join(lines)


from config_douyin import TODAY

async def tts_one(text, output_path):
    communicate = edge_tts.Communicate(text, TTS_VOICE)
    await communicate.save(output_path)


def main():
    ensure_dirs()

    data_path = os.path.join(DATA_DIR, "douyin_hot.json")
    with open(data_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"[Phase 7] 为 {len(items)} 条热搜生成配音 ({TTS_VOICE})...")

    narrations = []

    # 0. 封面开场白
    intro_text = generate_intro(items)
    intro_path = os.path.join(AUDIO_DIR, "narration_00_intro.mp3")
    narrations.append({"rank": 0, "text": intro_text, "type": "intro"})
    print(f"  开场白 ({len(intro_text)}字)...")
    asyncio.run(tts_one(intro_text, intro_path))
    print(f"  已保存: {intro_path}")
    # 生成字幕
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
        asyncio.run(tts_one(narration, output_path))
        print(f"  已保存: {output_path}")
        # 生成字幕
        dur = get_audio_duration(output_path)
        srt_path = os.path.join(SUBTITLES_DIR, f"sub_{rank:02d}.srt")
        generate_srt(narration, dur, srt_path)

    # 保存文案
    narrations_path = os.path.join(DATA_DIR, "narrations.json")
    with open(narrations_path, "w", encoding="utf-8") as f:
        json.dump(narrations, f, ensure_ascii=False, indent=2)

    print(f"[Phase 7] 完成! (配音 + 字幕)")


if __name__ == "__main__":
    main()

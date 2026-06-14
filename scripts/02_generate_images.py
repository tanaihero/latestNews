"""
Phase 2: Generate bilingual dual-page card images (1080x1920)
  Page 1: 项目概览 — 名称、星标、描述（英文+中文标注）、头像
  Page 2: README 中文摘要 — 从 GitHub 拉取完整 README 并生成中文摘要
"""
import json
import sys
import os
import re
import requests
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    ensure_dirs, DATA_DIR, IMAGES_DIR,
    VIDEO_WIDTH, VIDEO_HEIGHT,
    FONT_CN, FONT_EN, FONT_CN_PINGFANG, TODAY
)
from lib.drawing import (
    get_font, draw_gradient_rect, draw_glow_circle,
    draw_text_centered, draw_text_wrapped_centered, draw_rounded_image
)

# === Sci-fi color scheme ===
COLORS = {
    "bg_dark": (10, 12, 20),
    "accent_blue": (0, 180, 255),
    "accent_cyan": (0, 255, 200),
    "text_white": (240, 242, 250),
    "text_gray": (160, 170, 190),
    "text_dim": (100, 110, 130),
    "star_gold": (255, 200, 50),
    "grid_line": (30, 35, 55),
}

# Per-rank gradient pairs
RANK_GRADIENTS = [
    ((255, 100, 50), (255, 200, 50)),    # #1 orange-gold
    ((0, 180, 255), (0, 255, 200)),       # #2 blue-cyan
    ((140, 80, 255), (200, 120, 255)),    # #3 purple
    ((0, 200, 150), (100, 255, 200)),     # #4 teal
    ((255, 80, 120), (255, 150, 180)),    # #5 pink
    ((80, 120, 255), (140, 180, 255)),    # #6 blue
    ((255, 180, 0), (255, 220, 100)),     # #7 gold
    ((0, 220, 180), (100, 255, 220)),     # #8 emerald
    ((200, 100, 255), (255, 150, 200)),   # #9 purple-pink
    ((100, 200, 255), (200, 230, 255)),   # #10 light blue
]

# === Keyword-based translation map ===
KEYWORD_MAP = {
    "framework": "框架", "library": "库", "tool": "工具",
    "API": "接口", "database": "数据库", "server": "服务器",
    "client": "客户端", "model": "模型", "AI": "人工智能",
    "machine learning": "机器学习", "deep learning": "深度学习",
    "compiler": "编译器", "language": "语言", "runtime": "运行时",
    "package": "包", "plugin": "插件", "extension": "扩展",
    "monitoring": "监控", "testing": "测试", "security": "安全",
    "authentication": "认证", "deployment": "部署", "container": "容器",
    "offline": "离线", "companion": "伴侣应用", "Bluetooth": "蓝牙",
    "audit": "审计", "codebase": "代码库", "cross-platform": "跨平台",
    "open source": "开源", "cloud": "云计算", "edge": "边缘计算",
    "agent": "智能体", "LLM": "大语言模型", "RAG": "检索增强生成",
    "fine-tune": "微调", "inference": "推理", "training": "训练",
    "neural network": "神经网络", "GPU": "图形处理器",
    "encryption": "加密", "vulnerability": "漏洞", "exploit": "漏洞利用",
    "automation": "自动化", "workflow": "工作流", "pipeline": "流水线",
    "microservice": "微服务", "kubernetes": "容器编排", "docker": "容器化",
    "web": "网页", "mobile": "移动端", "desktop": "桌面端",
    "performance": "性能", "optimization": "优化", "benchmark": "基准测试",
    "real-time": "实时", "streaming": "流式处理", "batch": "批处理",
    "natural language": "自然语言", "computer vision": "计算机视觉",
    "reinforcement learning": "强化学习", "generative": "生成式",
    "transformer": "Transformer架构", "embedding": "向量嵌入",
    "token": "令牌", "prompt": "提示词", "chatbot": "聊天机器人",
    "multi-modal": "多模态", "text-to-image": "文生图",
    "code generation": "代码生成", "code review": "代码审查",
}


# ─── README 获取与处理 ───────────────────────────────────────

HEADERS_GH = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "GitHub-Trending-Bot/1.0"
}
_gh_token = os.environ.get("GITHUB_TOKEN", "")
if _gh_token:
    HEADERS_GH["Authorization"] = f"token {_gh_token}"


def fetch_full_readme(full_name):
    """从 GitHub 获取完整 README 原文（最多 8000 字符）"""
    try:
        url = f"https://api.github.com/repos/{full_name}/readme"
        resp = requests.get(
            url,
            headers={**HEADERS_GH, "Accept": "application/vnd.github.v3.raw"},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.text[:8000]
    except Exception:
        pass
    return ""


def clean_markdown(text):
    """清洗 Markdown 为纯文本"""
    # 移除代码块
    text = re.sub(r'```[\s\S]*?```', '', text)
    # 移除 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 移除图片
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # 链接保留文字
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # 移除表格分隔线
    text = re.sub(r'\|[-:]+\|', '', text)
    # 移除标题 #
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    # 移除粗体/斜体
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}(.*?)_{1,3}', r'\1', text)
    # 移除行内代码
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # 移除列表符号
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    # 折叠空白
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def extract_key_paragraphs(text, max_chars=600):
    """从清洗后的 README 中提取关键段落（跳过标题、过短行）"""
    paragraphs = text.split('\n\n')
    result = []
    total = 0
    for p in paragraphs:
        p = p.strip()
        if not p or len(p) < 15:
            continue
        # 跳过纯标题行、表格、列表
        if p.startswith('#') or p.startswith('|') or p.startswith('-') or p.startswith('*'):
            continue
        # 跳过全是大写或全是符号的行
        alpha = [c for c in p if c.isalpha()]
        if len(alpha) < 10:
            continue
        result.append(p)
        total += len(p)
        if total >= max_chars:
            break
    summary = ' '.join(result)
    if len(summary) > max_chars:
        summary = summary[:max_chars - 3] + "..."
    return summary


def annotate_with_chinese(text):
    """将英文文本中的技术关键词标注中文翻译（Page 1 描述用）"""
    if not text:
        return "暂无详细信息"
    result = text
    sorted_keys = sorted(KEYWORD_MAP.keys(), key=len, reverse=True)
    for eng in sorted_keys:
        cn = KEYWORD_MAP[eng]
        if f"{eng}({cn})" in result:
            continue
        pattern = r'(?<![a-zA-Z])' + re.escape(eng) + r'(?![a-zA-Z(])'
        result = re.sub(pattern, f"{eng}({cn})", result, count=1)
    return result


def _is_chinese(text):
    """判断文本是否主要为中文"""
    if not text:
        return False
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    return ascii_chars / max(len(text), 1) < 0.5


def _extract_concepts(text):
    """从英文文本中提取匹配到的中文技术概念"""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    seen = set()
    for eng in sorted(KEYWORD_MAP.keys(), key=len, reverse=True):
        if eng.lower() in text_lower and KEYWORD_MAP[eng] not in seen:
            found.append(KEYWORD_MAP[eng])
            seen.add(KEYWORD_MAP[eng])
    return found


def generate_readme_summary(repo):
    """为一个项目生成中文摘要，返回 dict: {card_text, narration_text}

    card_text:    展示在 Page 2 卡片上的内容（中文标签 + 原文摘录）
    narration_text: 供 TTS 朗读的自然中文文本
    """
    desc = repo.get("description") or ""
    lang = repo.get("language") or "多语言"
    stars = repo.get("stars", 0)
    license_info = repo.get("license") or "未指定"
    topics = repo.get("topics") or []
    url = repo.get("url", "")

    # ── 1. 获取并清洗 README ──
    readme_raw = fetch_full_readme(repo["full_name"])
    if not readme_raw:
        readme_raw = repo.get("readme_preview", "")
    cleaned = clean_markdown(readme_raw) if readme_raw else ""
    readme_excerpt = extract_key_paragraphs(cleaned, max_chars=500) if cleaned else ""

    # ── 2. 提取描述中的技术概念（供卡片和配音共用）──
    desc_concepts = _extract_concepts(desc) if desc and desc != "暂无描述" else []

    # ── 3. 构建卡片展示文本（中文标签 + 内容摘录）──
    card_parts = []

    # 项目定位
    card_parts.append("【项目定位】")
    if desc and desc != "暂无描述":
        if _is_chinese(desc):
            card_parts.append(desc)
        else:
            concepts = desc_concepts
            if concepts:
                card_parts.append(f"一个关于{'、'.join(concepts[:4])}的{lang}开源项目")
            else:
                card_parts.append(f"一个{lang}开源项目")
            card_parts.append(f"原文：{desc[:200]}")
    else:
        card_parts.append("暂无项目描述")

    # 文档摘录
    if readme_excerpt:
        card_parts.append("")
        card_parts.append("【文档摘要】")
        card_parts.append(readme_excerpt[:400])

    # 基本信息
    card_parts.append("")
    card_parts.append("【基本信息】")
    card_parts.append(f"编程语言：{lang} | 星标：{format_stars(stars)}")
    if license_info and license_info not in ("未指定", "N/A", "NOASSERTION"):
        card_parts.append(f"开源协议：{license_info}")
    if topics:
        card_parts.append(f"标签：{', '.join(topics[:5])}")
    card_parts.append(f"仓库地址：{url}")

    card_text = "\n".join(card_parts)

    # ── 4. 构建 TTS 朗读文本（中文框架 + 英文原文，edge-tts 可处理中英混合）──
    narr = []
    if desc and desc != "暂无描述":
        if _is_chinese(desc):
            narr.append(f"这个项目的功能是：{desc}。")
        else:
            narr.append(f"这个项目的定位是：{desc}。")

    # README 朗读版：直接读清洗后的英文摘录（edge-tts 可朗读英文）
    if readme_excerpt:
        narr_excerpt = readme_excerpt[:300]
        if len(readme_excerpt) > 300:
            cut = narr_excerpt.rfind(".")
            if cut > 80:
                narr_excerpt = narr_excerpt[:cut + 1]
            else:
                narr_excerpt = narr_excerpt + "."
        if _is_chinese(narr_excerpt):
            narr.append(f"根据项目文档介绍，{narr_excerpt}")
        else:
            narr.append(f"根据项目文档介绍：{narr_excerpt}")

    if topics:
        narr.append(f"项目的标签包括{'、'.join(topics[:4])}。")
    if license_info and license_info not in ("未指定", "N/A", "NOASSERTION"):
        narr.append(f"采用{license_info}开源协议。")

    narration_text = "".join(narr) if narr else "该项目暂无详细的文档介绍。"

    return {"card_text": card_text, "narration_text": narration_text}


# ─── 图片绘制辅助 ──────────────────────────────────────────

def draw_grid_bg(img):
    """Draw grid background lines"""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    step = 60
    color = COLORS["grid_line"]
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=color, width=1)
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=color, width=1)


def draw_text_wrapped(draw, text, x, y, max_width, font, fill, line_spacing=8):
    """Left-aligned text wrapping. Returns total height used."""
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        bbox = font.getbbox(test_line)
        if bbox[2] - bbox[0] > max_width:
            if current_line:
                lines.append(current_line)
            current_line = char
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)

    total_height = 0
    for line in lines:
        bbox = font.getbbox(line)
        line_height = bbox[3] - bbox[1]
        draw.text((x, y + total_height), line, font=font, fill=fill)
        total_height += line_height + line_spacing
    return total_height


def format_stars(count):
    if count >= 1000:
        return f"{count / 1000:.1f}k"
    return str(count)


def download_avatar(url, size=200):
    try:
        resp = requests.get(url, timeout=10)
        img = Image.open(BytesIO(resp.content)).convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse([0, 0, size, size], fill=255)
        img.putalpha(mask)
        return img
    except Exception as e:
        print(f"  Avatar download failed: {e}")
        return None


# ─── Page 1: 项目概览卡片 ────────────────────────────────────

def generate_page1(repo, output_path):
    """Page 1: 项目概览 — 名称、星标、英文描述+中文标注、头像"""
    rank = repo["rank"]
    c1, c2 = RANK_GRADIENTS[(rank - 1) % len(RANK_GRADIENTS)]

    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), COLORS["bg_dark"])
    draw = ImageDraw.Draw(img)
    draw_grid_bg(img)

    img = draw_glow_circle(img, (VIDEO_WIDTH // 2, 200), 400, c1, 0.15)
    img = draw_glow_circle(img, (100, 600), 250, c2, 0.1)
    img = draw_glow_circle(img, (VIDEO_WIDTH - 100, 1400), 300, c1, 0.08)
    draw = ImageDraw.Draw(img)

    # 顶部渐变条
    draw_gradient_rect(draw, (0, 0, VIDEO_WIDTH, 6), c1, c2)

    # 字体
    font_header = get_font(FONT_CN, 36)
    font_sub = get_font(FONT_CN, 28)
    font_rank = get_font(FONT_EN, 72)
    font_name = get_font(FONT_CN, 56)
    font_owner = get_font(FONT_CN, 32)
    font_metric_val = get_font(FONT_EN, 44)
    font_metric_label = get_font(FONT_CN, 22)
    font_desc_en = get_font(FONT_CN, 36)
    font_desc_cn = get_font(FONT_CN, 28)
    font_tag = get_font(FONT_EN, 22)
    font_url = get_font(FONT_EN, 24)
    font_footer = get_font(FONT_CN, 26)
    font_page = get_font(FONT_CN, 20)

    # Header
    draw.text((60, 50), "GitHub 热门项目日报", font=font_header, fill=COLORS["text_white"])
    draw.text((60, 100), f"{TODAY}  |  TOP 10", font=font_sub, fill=COLORS["text_gray"])

    # 排名徽章
    badge_size = 140
    badge_x = (VIDEO_WIDTH - badge_size) // 2
    badge_y = 160
    draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size], fill=c1)
    draw.ellipse([badge_x + 4, badge_y + 4, badge_x + badge_size - 4, badge_y + badge_size - 4],
                 fill=COLORS["bg_dark"])
    draw.ellipse([badge_x + 8, badge_y + 8, badge_x + badge_size - 8, badge_y + badge_size - 8],
                 fill=c1)
    rank_text = f"#{rank}"
    bbox = font_rank.getbbox(rank_text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((badge_x + (badge_size - tw) // 2, badge_y + (badge_size - th) // 2 - 8),
              rank_text, font=font_rank, fill=COLORS["bg_dark"])

    # 项目名
    y_name = 320
    name = repo["name"]
    bbox = font_name.getbbox(name)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, y_name), name, font=font_name, fill=COLORS["text_white"])

    # 作者
    y_owner = 390
    owner_text = f"by {repo['owner']}"
    bbox = font_owner.getbbox(owner_text)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, y_owner), owner_text, font=font_owner, fill=COLORS["text_gray"])

    # 头像
    avatar_size = 180
    y_avatar = 430
    avatar = download_avatar(repo["owner_avatar"], avatar_size)
    if avatar:
        avatar_x = (VIDEO_WIDTH - avatar_size) // 2
        border = 4
        draw.ellipse([avatar_x - border, y_avatar - border,
                       avatar_x + avatar_size + border, y_avatar + avatar_size + border], fill=c1)
        img.paste(avatar, (avatar_x, y_avatar), avatar)
    y_after_avatar = y_avatar + avatar_size + 20

    # 数据卡片
    card_y = 650
    card_margin = 40
    card_width = VIDEO_WIDTH - card_margin * 2
    card_height = 140
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [card_margin, card_y, card_margin + card_width, card_y + card_height],
        radius=16, fill=(25, 30, 50, 200),
    )
    overlay_draw.line(
        [(card_margin + 16, card_y), (card_margin + card_width - 16, card_y)],
        fill=(*c1, 120), width=2,
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)

    metrics = [
        (format_stars(repo["stars"]), "Stars · 星标"),
        (format_stars(repo["forks"]), "Forks · 分支"),
        (repo["language"] or "N/A", "Language · 语言"),
    ]
    col_width = card_width // 3
    for i, (val, label) in enumerate(metrics):
        mx = card_margin + col_width * i + col_width // 2
        bbox = font_metric_val.getbbox(val)
        vw = bbox[2] - bbox[0]
        draw.text((mx - vw // 2, card_y + 22), val, font=font_metric_val, fill=COLORS["text_white"])
        bbox = font_metric_label.getbbox(label)
        lw = bbox[2] - bbox[0]
        draw.text((mx - lw // 2, card_y + 85), label, font=font_metric_label, fill=COLORS["text_gray"])

    # 描述
    y = 830
    desc = repo.get("description") or ""
    if not desc or desc.strip() == "":
        desc = "暂无描述"

    if desc == "暂无描述":
        draw.text((60, y), "暂无描述", font=font_desc_cn, fill=COLORS["text_gray"])
        y += 50
    else:
        en_text = desc if len(desc) <= 150 else desc[:147] + "..."
        en_height = draw_text_wrapped(draw, en_text, 60, y, VIDEO_WIDTH - 120,
                                       font_desc_en, COLORS["text_white"], line_spacing=12)
        y += en_height + 16

        # 中文关键词标注
        cn_text = annotate_with_chinese(desc)
        if cn_text != desc:
            if len(cn_text) > 200:
                cn_text = cn_text[:197] + "..."
            cn_height = draw_text_wrapped(draw, cn_text, 60, y, VIDEO_WIDTH - 120,
                                           font_desc_cn, COLORS["text_gray"], line_spacing=10)
            y += cn_height + 16
        else:
            y += 8

    # Topics 标签
    topics = repo.get("topics") or []
    if topics:
        tag_x = 60
        tag_y = y + 10
        for topic in topics[:5]:
            tag_text = f"#{topic}"
            bbox = font_tag.getbbox(tag_text)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if tag_x + tw + 30 > VIDEO_WIDTH - 60:
                break
            draw.rounded_rectangle([tag_x, tag_y, tag_x + tw + 20, tag_y + th + 14],
                                   radius=8, outline=c1, width=1)
            draw.text((tag_x + 10, tag_y + 5), tag_text, font=font_tag, fill=c1)
            tag_x += tw + 36
        y = tag_y + th + 30

    # License + 创建时间
    info_y = y + 10
    license_info = repo.get("license") or "未指定"
    created = repo.get("created_at", "")[:10]
    info_parts = []
    if license_info and license_info not in ("未指定", "N/A", "NOASSERTION"):
        info_parts.append(f"License: {license_info}")
    if created:
        info_parts.append(f"Created: {created}")
    if info_parts:
        info_text = "  |  ".join(info_parts)
        bbox = font_sub.getbbox(info_text)
        tw = bbox[2] - bbox[0]
        draw.text(((VIDEO_WIDTH - tw) // 2, info_y), info_text,
                  font=font_sub, fill=COLORS["text_dim"])

    # URL
    url_text = repo["url"]
    bbox = font_url.getbbox(url_text)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, 1760), url_text, font=font_url, fill=COLORS["text_dim"])

    # Footer
    footer = "GitHub 热门项目 · 每日精选"
    bbox = font_footer.getbbox(footer)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, 1840), footer, font=font_footer, fill=COLORS["text_gray"])

    # 页码提示
    page_hint = "1 / 2"
    bbox = font_page.getbbox(page_hint)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, 1880), page_hint, font=font_page, fill=COLORS["text_dim"])

    # 底部渐变条
    draw_gradient_rect(draw, (0, VIDEO_HEIGHT - 6, VIDEO_WIDTH, VIDEO_HEIGHT), c2, c1)

    if img.mode == "RGBA":
        img = img.convert("RGB")
    img.save(output_path, "PNG", quality=95)


# ─── Page 2: README 中文摘要卡片 ────────────────────────────

def generate_page2(repo, summary_data, output_path):
    """Page 2: README 中文摘要 — 结构化中文内容（项目定位 + 文档摘要 + 基本信息）"""
    rank = repo["rank"]
    c1, c2 = RANK_GRADIENTS[(rank - 1) % len(RANK_GRADIENTS)]

    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), COLORS["bg_dark"])
    draw = ImageDraw.Draw(img)
    draw_grid_bg(img)

    img = draw_glow_circle(img, (VIDEO_WIDTH // 2, 400), 350, c2, 0.12)
    img = draw_glow_circle(img, (VIDEO_WIDTH - 150, 900), 280, c1, 0.10)
    img = draw_glow_circle(img, (150, 1500), 300, c2, 0.08)
    draw = ImageDraw.Draw(img)

    draw_gradient_rect(draw, (0, 0, VIDEO_WIDTH, 6), c1, c2)

    # 字体
    font_header = get_font(FONT_CN, 36)
    font_sub = get_font(FONT_CN, 28)
    font_rank = get_font(FONT_EN, 48)
    font_name = get_font(FONT_CN, 52)
    font_owner = get_font(FONT_CN, 28)
    font_section = get_font(FONT_CN, 30)
    font_body = get_font(FONT_CN, 28)
    font_body_en = get_font(FONT_CN, 24)
    font_info = get_font(FONT_CN, 24)
    font_tag = get_font(FONT_EN, 22)
    font_url = get_font(FONT_EN, 22)
    font_footer = get_font(FONT_CN, 26)
    font_page = get_font(FONT_CN, 20)

    # Header
    draw.text((60, 50), "GitHub 热门项目日报", font=font_header, fill=COLORS["text_white"])
    rank_text = f"#{rank}"
    bbox = font_rank.getbbox(rank_text)
    draw.text((60, 110), rank_text, font=font_rank, fill=c1)
    rx = 60 + (bbox[2] - bbox[0]) + 16
    draw.text((rx, 120), "项目详细介绍", font=font_sub, fill=COLORS["text_gray"])
    draw_gradient_rect(draw, (60, 175, VIDEO_WIDTH - 60, 178), c1, c2)

    # 项目名 + 作者
    y = 200
    name = repo["name"]
    bbox = font_name.getbbox(name)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, y), name, font=font_name, fill=COLORS["text_white"])
    y += 70
    owner_text = f"by {repo['owner']}"
    bbox = font_owner.getbbox(owner_text)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, y), owner_text, font=font_owner, fill=COLORS["text_gray"])
    y += 50

    # ── 解析结构化摘要并逐段渲染 ──
    card_text = summary_data.get("card_text", "") if isinstance(summary_data, dict) else str(summary_data)
    text_width = VIDEO_WIDTH - 160

    sections = card_text.split("\n")
    i = 0
    while i < len(sections):
        line = sections[i].strip()

        if line.startswith("【") and line.endswith("】"):
            # 段落标题
            if y > 1650:
                break
            y += 12
            # 装饰竖线 + 标题
            draw.rectangle([60, y, 66, y + 32], fill=c1)
            draw.text((76, y), line, font=font_section, fill=c1)
            y += 44

            # 收集该段落下的正文行
            body_lines = []
            i += 1
            while i < len(sections):
                next_line = sections[i].strip()
                if not next_line:
                    i += 1
                    continue
                if next_line.startswith("【"):
                    break
                body_lines.append(next_line)
                i += 1

            if not body_lines:
                continue

            # 判断是否为"原文："行（用较小英文字体）
            is_original = body_lines[0].startswith("原文：")

            # 测量文字高度
            temp_img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), COLORS["bg_dark"])
            temp_draw = ImageDraw.Draw(temp_img)
            body_font = font_body_en if is_original else font_body
            body_color = COLORS["text_gray"] if is_original else COLORS["text_white"]
            total_h = 0
            for bl in body_lines:
                h = draw_text_wrapped(temp_draw, bl, 0, 0, text_width,
                                       body_font, body_color, line_spacing=10)
                total_h += h + 6

            # 背景框
            if total_h > 0:
                box_h = total_h + 24
                overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
                od = ImageDraw.Draw(overlay)
                od.rounded_rectangle([50, y, VIDEO_WIDTH - 50, y + box_h],
                                     radius=12, fill=(20, 25, 42, 160))
                img = Image.alpha_composite(img.convert("RGBA"), overlay)
                draw = ImageDraw.Draw(img)

                # 绘制正文
                cy = y + 12
                for bl in body_lines:
                    dh = draw_text_wrapped(draw, bl, 80, cy, text_width,
                                            body_font, body_color, line_spacing=10)
                    cy += dh + 6
                y = y + box_h + 8
        else:
            # 非段落行（如基本信息中的普通行）
            if line:
                draw.text((80, y), line, font=font_info, fill=COLORS["text_gray"])
                y += 36
            i += 1

    # Topics 标签
    topics = repo.get("topics") or []
    if topics and y < 1600:
        y += 10
        draw.rectangle([60, y, 66, y + 28], fill=c1)
        draw.text((76, y), "【相关标签】", font=font_section, fill=c1)
        y += 44
        tag_x = 80
        for topic in topics[:8]:
            tag_text = f"#{topic}"
            bbox = font_tag.getbbox(tag_text)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if tag_x + tw + 30 > VIDEO_WIDTH - 60:
                tag_x = 80
                y += th + 20
            draw.rounded_rectangle([tag_x, y, tag_x + tw + 20, y + th + 14],
                                   radius=8, outline=c1, width=1)
            draw.text((tag_x + 10, y + 5), tag_text, font=font_tag, fill=c1)
            tag_x += tw + 36
        y += th + 30

    # 底部数据行
    stars = format_stars(repo["stars"])
    forks = format_stars(repo["forks"])
    lang = repo.get("language") or "N/A"
    summary_line = f"{stars} Stars  |  {forks} Forks  |  {lang}"
    bbox = font_sub.getbbox(summary_line)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, 1720), summary_line, font=font_sub, fill=COLORS["text_dim"])

    url_text = repo["url"]
    bbox = font_url.getbbox(url_text)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, 1770), url_text, font=font_url, fill=COLORS["text_dim"])

    footer = "GitHub 热门项目 · 每日精选"
    bbox = font_footer.getbbox(footer)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, 1840), footer, font=font_footer, fill=COLORS["text_gray"])

    page_hint = "2 / 2"
    bbox = font_page.getbbox(page_hint)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, 1880), page_hint, font=font_page, fill=COLORS["text_dim"])

    draw_gradient_rect(draw, (0, VIDEO_HEIGHT - 6, VIDEO_WIDTH, VIDEO_HEIGHT), c2, c1)

    if img.mode == "RGBA":
        img = img.convert("RGB")
    img.save(output_path, "PNG", quality=95)


# ─── 封面缩略图 ──────────────────────────────────────────────

def generate_thumbnail(repos, output_path):
    """封面缩略图 — 列出 Top 10 项目"""
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), COLORS["bg_dark"])
    draw = ImageDraw.Draw(img)
    draw_grid_bg(img)
    img = draw_glow_circle(img, (VIDEO_WIDTH // 2, VIDEO_HEIGHT // 3), 500, (0, 180, 255), 0.2)
    img = draw_glow_circle(img, (200, VIDEO_HEIGHT * 2 // 3), 300, (140, 80, 255), 0.12)
    draw = ImageDraw.Draw(img)

    font_title = get_font(FONT_CN, 72)
    font_sub = get_font(FONT_CN, 40)
    font_list = get_font(FONT_CN, 34)
    font_footer = get_font(FONT_CN, 28)

    title = "GitHub 热门项目"
    bbox = font_title.getbbox(title)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, 200), title, font=font_title, fill=COLORS["text_white"])

    subtitle = f"TOP 10 日报  |  {TODAY}"
    bbox = font_sub.getbbox(subtitle)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, 300), subtitle, font=font_sub, fill=COLORS["accent_cyan"])

    draw_gradient_rect(draw, (200, 380, VIDEO_WIDTH - 200, 384),
                       COLORS["accent_blue"], COLORS["accent_cyan"])

    y = 440
    for repo in repos:
        rank = repo["rank"]
        c1, _ = RANK_GRADIENTS[(rank - 1) % len(RANK_GRADIENTS)]
        text = f"#{rank}  {repo['name']}"
        stars = format_stars(repo["stars"])
        draw.text((100, y), text, font=font_list, fill=COLORS["text_white"])
        bbox = font_list.getbbox(f"* {stars}")
        draw.text((VIDEO_WIDTH - 100 - (bbox[2] - bbox[0]), y),
                  f"* {stars}", font=font_list, fill=COLORS["star_gold"])
        y += 60

    footer = "GitHub 热门项目 · 每日精选"
    bbox = font_footer.getbbox(footer)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, VIDEO_HEIGHT - 120),
              footer, font=font_footer, fill=COLORS["text_gray"])

    draw_gradient_rect(draw, (0, VIDEO_HEIGHT - 6, VIDEO_WIDTH, VIDEO_HEIGHT),
                       COLORS["accent_blue"], COLORS["accent_cyan"])

    if img.mode == "RGBA":
        img = img.convert("RGB")
    img.save(output_path, "PNG", quality=95)
    print(f"  Thumbnail saved: {output_path}")


# ─── Main ─────────────────────────────────────────────────────

def main():
    ensure_dirs()

    data_path = os.path.join(DATA_DIR, "repos.json")
    with open(data_path, "r", encoding="utf-8") as f:
        repos = json.load(f)

    print(f"[Phase 2] 生成 {len(repos)} 个项目的双页卡片...")

    # 1. 拉取 README 并生成中文摘要
    print("  [Step 1] 获取 README 并生成中文摘要...")
    for repo in repos:
        summary = generate_readme_summary(repo)
        repo["readme_summary_cn"] = summary  # dict: {card_text, narration_text}
        print(f"    #{repo['rank']} {repo['name']}: card={len(summary['card_text'])}字, narr={len(summary['narration_text'])}字")

    # 保存更新后的数据（供 Phase 3 使用）
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(repos, f, ensure_ascii=False, indent=2)
    print("  已更新 repos.json (含 readme_summary_cn)")

    # 2. 生成双页卡片
    print("  [Step 2] 生成卡片图片...")
    for repo in repos:
        rank = repo["rank"]
        page1_path = os.path.join(IMAGES_DIR, f"repo_{rank:02d}_p1.png")
        page2_path = os.path.join(IMAGES_DIR, f"repo_{rank:02d}_p2.png")
        generate_page1(repo, page1_path)
        print(f"    Page 1 saved: {page1_path}")
        generate_page2(repo, repo.get("readme_summary_cn", {}), page2_path)
        print(f"    Page 2 saved: {page2_path}")

    # 3. 封面缩略图
    thumbnail_path = os.path.join(IMAGES_DIR, "thumbnail.png")
    generate_thumbnail(repos, thumbnail_path)

    print(f"[Phase 2] 完成! 所有图片已保存到: {IMAGES_DIR}")


if __name__ == "__main__":
    main()

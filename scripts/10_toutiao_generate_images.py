"""
Phase 10: 头条热榜卡片图片生成 (1080x1920)
复用 lib/drawing.py 共享工具，头条红主色调。
"""
import json
import sys
import os

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_toutiao import (
    ensure_dirs, DATA_DIR, IMAGES_DIR,
    VIDEO_WIDTH, VIDEO_HEIGHT,
    FONT_CN, FONT_EN, TODAY
)
from lib.drawing import (
    get_font, draw_gradient_rect, draw_glow_circle,
    draw_rounded_image, draw_text_centered, draw_text_wrapped_centered,
    format_hot_value, draw_flame, load_cover_image
)

# === 头条配色（红/暖色系） ===
BG_COLOR = (20, 10, 12)
TEXT_WHITE = (245, 245, 255)
TEXT_GRAY = (200, 180, 180)
TEXT_DIM = (140, 110, 110)

RANK_COLORS = [
    ((255, 50, 50), (255, 130, 30)),    # 1: 红-橙
    ((255, 80, 30), (255, 180, 50)),    # 2: 橙红-金
    ((230, 50, 80), (255, 100, 60)),    # 3: 深红-橙
    ((255, 120, 50), (255, 200, 80)),   # 4: 橙-金
    ((220, 60, 60), (255, 150, 50)),    # 5: 红-橙
    ((200, 50, 80), (240, 120, 80)),    # 6: 暗红-橙
    ((255, 100, 60), (255, 180, 100)),  # 7: 橙-浅金
    ((180, 50, 50), (220, 100, 60)),    # 8: 深红-暗橙
    ((240, 80, 40), (255, 160, 80)),    # 9: 红橙-金
    ((200, 60, 60), (255, 120, 60)),    # 10: 暗红-橙
]

LABEL_MAP = {
    1: ("新", (0, 180, 100)),
    2: ("热", (255, 60, 60)),
    3: ("沸", (255, 100, 0)),
    4: ("爆", (255, 30, 30)),
}


def generate_card(item, max_hot, output_path):
    """生成单张头条热榜卡片"""
    rank = item["rank"]
    c1, c2 = RANK_COLORS[(rank - 1) % len(RANK_COLORS)]
    has_cover = bool(item.get("local_cover"))

    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 1. 背景网格
    step = 80
    for x in range(0, VIDEO_WIDTH, step):
        draw.line([(x, 0), (x, VIDEO_HEIGHT)], fill=(30, 18, 20), width=1)
    for y in range(0, VIDEO_HEIGHT, step):
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(30, 18, 20), width=1)

    # 2. 发光装饰
    img = draw_glow_circle(img, (VIDEO_WIDTH // 2, 300), 400, c1, 0.15)
    img = draw_glow_circle(img, (100, 1000), 280, c2, 0.08)
    img = draw_glow_circle(img, (VIDEO_WIDTH - 100, 1600), 300, c1, 0.06)
    draw = ImageDraw.Draw(img)

    # 3. 顶部渐变条
    draw_gradient_rect(draw, (0, 0, VIDEO_WIDTH, 8), c1, c2)

    # === 顶部标题区域 ===
    y = 50
    font_brand = get_font(FONT_CN, 44, FONT_CN)
    font_date = get_font(FONT_CN, 26, FONT_CN)

    draw.text((60, y), "头条热榜", font=font_brand, fill=c1)
    draw.text((60, y + 55), f"{TODAY}  |  TOP 10", font=font_date, fill=TEXT_GRAY)

    # === 排名徽章 ===
    y = 140
    rank_size = 120
    rank_x = (VIDEO_WIDTH - rank_size) // 2
    draw.ellipse([rank_x, y, rank_x + rank_size, y + rank_size], fill=c1)
    draw.ellipse([rank_x + 5, y + 5, rank_x + rank_size - 5, y + rank_size - 5], fill=BG_COLOR)
    draw.ellipse([rank_x + 10, y + 10, rank_x + rank_size - 10, y + rank_size - 10], fill=c1)

    font_rank = get_font(FONT_EN, 60, FONT_CN)
    rank_text = f"#{rank}"
    bbox = font_rank.getbbox(rank_text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((rank_x + (rank_size - tw) // 2, y + (rank_size - th) // 2 - 6),
              rank_text, font=font_rank, fill=(255, 255, 255))

    if rank <= 3:
        draw_flame(draw, rank_x + rank_size + 35, y + rank_size // 2, 20, (255, 120, 30))
        if rank <= 2:
            draw_flame(draw, rank_x - 35, y + rank_size // 2, 20, (255, 120, 30))

    y += rank_size + 20

    # === 封面图区域 ===
    cover_img = None
    if has_cover:
        cover_img = load_cover_image(item["local_cover"])

    if cover_img:
        cover_w = 900
        cw, ch = cover_img.size
        aspect = ch / cw
        cover_h = min(int(cover_w * aspect), 500)
        cover_x = (VIDEO_WIDTH - cover_w) // 2

        border = 4
        draw.rectangle(
            [cover_x - border, y - border, cover_x + cover_w + border, y + cover_h + border],
            fill=c1
        )
        draw.rectangle(
            [cover_x - border + 2, y - border + 2,
             cover_x + cover_w + border - 2, y + cover_h + border - 2],
            fill=c2
        )
        draw.rectangle(
            [cover_x, y, cover_x + cover_w, y + cover_h],
            fill=BG_COLOR
        )

        draw_rounded_image(img, cover_img, (cover_x, y), (cover_w, cover_h), radius=16)
        draw = ImageDraw.Draw(img)

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        fade_start = y + cover_h - 60
        for fy in range(fade_start, y + cover_h):
            alpha = int(255 * ((fy - fade_start) / 60))
            overlay_draw.line(
                [(cover_x, fy), (cover_x + cover_w, fy)],
                fill=(BG_COLOR[0], BG_COLOR[1], BG_COLOR[2], alpha)
            )
        img = Image.alpha_composite(img.convert("RGBA"), overlay)
        draw = ImageDraw.Draw(img)

        y += cover_h + 25
    else:
        y += 20
        placeholder_w = 900
        placeholder_h = 200
        px = (VIDEO_WIDTH - placeholder_w) // 2
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rounded_rectangle(
            [px, y, px + placeholder_w, y + placeholder_h],
            radius=20, fill=(40, 20, 22, 180)
        )
        img = Image.alpha_composite(img.convert("RGBA"), overlay)
        draw = ImageDraw.Draw(img)
        font_ph = get_font(FONT_CN, 36, FONT_CN)
        ph_text = "热榜话题"
        bbox = font_ph.getbbox(ph_text)
        pw = bbox[2] - bbox[0]
        draw.text(((VIDEO_WIDTH - pw) // 2, y + (placeholder_h - 40) // 2),
                  ph_text, font=font_ph, fill=TEXT_DIM)
        y += placeholder_h + 25

    # === 标签徽章 ===
    label_info = LABEL_MAP.get(item.get("label", 0))
    if label_info:
        label_text, label_color = label_info
        font_label = get_font(FONT_CN, 28, FONT_CN)
        bbox = font_label.getbbox(label_text)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        badge_x = (VIDEO_WIDTH - lw - 30) // 2
        draw.rounded_rectangle(
            [badge_x, y, badge_x + lw + 30, y + lh + 16],
            radius=16, fill=label_color
        )
        draw.text((badge_x + 15, y + 6), label_text, font=font_label, fill=(255, 255, 255))
        y += lh + 35

    # === 热搜话题文字 ===
    y += 10
    font_topic = get_font(FONT_CN, 58, FONT_CN)
    word = item["word"]
    max_text_width = VIDEO_WIDTH - 120

    test_bbox = font_topic.getbbox(word)
    if (test_bbox[2] - test_bbox[0]) > max_text_width:
        font_topic = get_font(FONT_CN, 46, FONT_CN)
    if (font_topic.getbbox(word)[2] - font_topic.getbbox(word)[0]) > max_text_width:
        font_topic = get_font(FONT_CN, 38, FONT_CN)

    h = draw_text_wrapped_centered(draw, word, y, max_text_width, font_topic, TEXT_WHITE,
                                    canvas_width=VIDEO_WIDTH)
    y += h + 25

    # === 热度进度条 ===
    hot_value = item.get("hot_value", 0)
    bar_margin = 80
    bar_width = VIDEO_WIDTH - bar_margin * 2
    bar_height = 20

    font_hot_label = get_font(FONT_CN, 24, FONT_CN)
    draw.text((bar_margin, y), "热度指数", font=font_hot_label, fill=TEXT_GRAY)
    hot_text = format_hot_value(hot_value)
    font_hot_val = get_font(FONT_CN, 28, FONT_CN)
    bbox = font_hot_val.getbbox(hot_text)
    hw = bbox[2] - bbox[0]
    draw.text((VIDEO_WIDTH - bar_margin - hw, y), hot_text, font=font_hot_val, fill=c1)

    y += 38
    draw.rounded_rectangle(
        [bar_margin, y, bar_margin + bar_width, y + bar_height],
        radius=bar_height // 2, fill=(50, 25, 28)
    )
    ratio = min(hot_value / max(max_hot, 1), 1.0)
    fill_w = int(bar_width * ratio)
    if fill_w > 0:
        draw_gradient_rect(draw, (bar_margin, y, bar_margin + fill_w, y + bar_height),
                           c1, c2, "horizontal")
    y += bar_height + 25

    # === 信息卡片 ===
    card_margin = 60
    card_width = VIDEO_WIDTH - card_margin * 2
    card_height = 140

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [card_margin, y, card_margin + card_width, y + card_height],
        radius=18, fill=(40, 20, 22, 200)
    )
    overlay_draw.line(
        [(card_margin + 16, y), (card_margin + card_width - 16, y)],
        fill=(*c1, 100), width=2
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)

    font_card_title = get_font(FONT_CN, 24, FONT_CN)
    font_card_val = get_font(FONT_CN, 34, FONT_CN)

    col_w = card_width // 3
    metrics = [
        ("当前排名", f"第 {rank} 名", TEXT_WHITE),
        ("热搜指数", format_hot_value(hot_value), c1),
    ]
    if item.get("video_count"):
        metrics.append(("相关讨论", f"{item['video_count']} 条", TEXT_WHITE))
    else:
        metrics.append(("热度占比", f"{ratio * 100:.0f}%", TEXT_WHITE))

    for i, (title, value, val_color) in enumerate(metrics):
        cx = card_margin + col_w * i + col_w // 2
        bbox = font_card_title.getbbox(title)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, y + 22), title, font=font_card_title, fill=TEXT_GRAY)
        bbox = font_card_val.getbbox(value)
        vw = bbox[2] - bbox[0]
        draw.text((cx - vw // 2, y + 60), value, font=font_card_val, fill=val_color)

    y += card_height + 30

    # === 大号水印 ===
    font_watermark = get_font(FONT_CN, 100, FONT_CN)
    wm_text = "热榜"
    bbox = font_watermark.getbbox(wm_text)
    wm_w = bbox[2] - bbox[0]
    wm_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    wm_draw = ImageDraw.Draw(wm_overlay)
    wm_x = (VIDEO_WIDTH - wm_w) // 2
    wm_y = y + 40
    wm_draw.text((wm_x, wm_y), wm_text, font=font_watermark, fill=(*c2, 20))
    img = Image.alpha_composite(img, wm_overlay)
    draw = ImageDraw.Draw(img)

    # 底部装饰圆点
    deco_y = VIDEO_HEIGHT - 160
    for dx, color, size in [
        (70, c1, 10), (110, c2, 6),
        (VIDEO_WIDTH - 120, c2, 10), (VIDEO_WIDTH - 80, c1, 6),
    ]:
        draw.ellipse([dx - size, deco_y - size, dx + size, deco_y + size], fill=color)

    # 底部标语
    font_footer = get_font(FONT_CN, 26, FONT_CN)
    footer_text = "头条热榜 . 每日热点追踪"
    bbox = font_footer.getbbox(footer_text)
    fw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - fw) // 2, VIDEO_HEIGHT - 80),
              footer_text, font=font_footer, fill=TEXT_DIM)

    draw_gradient_rect(draw, (0, VIDEO_HEIGHT - 8, VIDEO_WIDTH, VIDEO_HEIGHT), c2, c1)

    if img.mode == "RGBA":
        img = img.convert("RGB")
    img.save(output_path, "PNG", quality=95)
    print(f"  卡片已生成: {output_path}")


def generate_thumbnail(items, max_hot, output_path):
    """生成封面缩略图"""
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    step = 80
    for x in range(0, VIDEO_WIDTH, step):
        draw.line([(x, 0), (x, VIDEO_HEIGHT)], fill=(30, 18, 20), width=1)
    for y in range(0, VIDEO_HEIGHT, step):
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(30, 18, 20), width=1)

    img = draw_glow_circle(img, (VIDEO_WIDTH // 2, VIDEO_HEIGHT // 3), 500, (255, 50, 50), 0.18)
    img = draw_glow_circle(img, (200, VIDEO_HEIGHT * 2 // 3), 350, (255, 130, 30), 0.12)
    img = draw_glow_circle(img, (VIDEO_WIDTH - 200, VIDEO_HEIGHT // 2), 300, (255, 80, 30), 0.08)
    draw = ImageDraw.Draw(img)

    font_title = get_font(FONT_CN, 76, FONT_CN)
    font_sub = get_font(FONT_CN, 38, FONT_CN)
    font_list = get_font(FONT_CN, 34, FONT_CN)
    font_hot = get_font(FONT_CN, 26, FONT_CN)

    title = "头条热榜"
    bbox = font_title.getbbox(title)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, 180), title, font=font_title, fill=(255, 50, 50))

    subtitle = f"TOP 10  |  {TODAY}"
    bbox = font_sub.getbbox(subtitle)
    tw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - tw) // 2, 280), subtitle, font=font_sub, fill=(255, 180, 50))

    draw_gradient_rect(draw, (200, 350, VIDEO_WIDTH - 200, 356),
                       (255, 50, 50), (255, 180, 50))

    y = 410
    for item in items:
        rank = item["rank"]
        c1, _ = RANK_COLORS[(rank - 1) % len(RANK_COLORS)]

        thumb_size = 50
        if item.get("local_cover"):
            try:
                cover = Image.open(item["local_cover"]).convert("RGB")
                sw, sh = cover.size
                sc = max(thumb_size / sw, thumb_size / sh)
                nw, nh = int(sw * sc), int(sh * sc)
                cover = cover.resize((nw, nh), Image.LANCZOS)
                cl = (nw - thumb_size) // 2
                ct = (nh - thumb_size) // 2
                cover = cover.crop((cl, ct, cl + thumb_size, ct + thumb_size))
                mask = Image.new("L", (thumb_size, thumb_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([0, 0, thumb_size, thumb_size], radius=8, fill=255)
                cover.putalpha(mask)
                img.paste(cover, (70, y + 3), cover)
            except Exception:
                pass

        font_r = get_font(FONT_EN, 34, FONT_CN)
        draw.text((130, y), f"#{rank:>2}", font=font_r, fill=c1)

        word = item["word"]
        if len(word) > 16:
            word = word[:14] + "..."
        draw.text((220, y), word, font=font_list, fill=TEXT_WHITE)

        hot_text = format_hot_value(item["hot_value"])
        bbox = font_hot.getbbox(hot_text)
        hw = bbox[2] - bbox[0]
        draw.text((VIDEO_WIDTH - 70 - hw, y + 5), hot_text, font=font_hot, fill=c1)

        y += 65

    draw_gradient_rect(draw, (0, VIDEO_HEIGHT - 8, VIDEO_WIDTH, VIDEO_HEIGHT),
                       (255, 50, 50), (255, 180, 50))
    font_footer = get_font(FONT_CN, 28, FONT_CN)
    footer = "每日热榜 . 一键速览"
    bbox = font_footer.getbbox(footer)
    fw = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - fw) // 2, VIDEO_HEIGHT - 80), footer, font=font_footer, fill=TEXT_DIM)

    if img.mode == "RGBA":
        img = img.convert("RGB")
    img.save(output_path, "PNG", quality=95)
    print(f"  封面已生成: {output_path}")


def main():
    ensure_dirs()

    data_path = os.path.join(DATA_DIR, "toutiao_hot.json")
    with open(data_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    max_hot = max(item["hot_value"] for item in items) if items else 1

    print(f"[Phase 10] 正在生成 {len(items)} 张头条热榜卡片...")

    for item in items:
        output_path = os.path.join(IMAGES_DIR, f"hot_{item['rank']:02d}.png")
        generate_card(item, max_hot, output_path)

    thumbnail_path = os.path.join(IMAGES_DIR, "thumbnail.png")
    generate_thumbnail(items, max_hot, thumbnail_path)

    print(f"[Phase 10] 完成! 所有图片保存在: {IMAGES_DIR}")


if __name__ == "__main__":
    main()

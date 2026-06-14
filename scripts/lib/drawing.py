"""
共享 PIL 绘图工具库
从抖音脚本提取，供所有平台复用。
"""
from PIL import Image, ImageDraw, ImageFont


def get_font(path, size, fallback_path=None):
    """加载字体，失败时回退"""
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        if fallback_path:
            try:
                return ImageFont.truetype(fallback_path, size)
            except Exception:
                pass
        return ImageFont.load_default()


def draw_gradient_rect(draw, bbox, color1, color2, direction="horizontal"):
    """绘制渐变矩形"""
    x1, y1, x2, y2 = bbox
    if direction == "horizontal":
        for x in range(x1, x2):
            ratio = (x - x1) / max(x2 - x1, 1)
            r = int(color1[0] + (color2[0] - color1[0]) * ratio)
            g = int(color1[1] + (color2[1] - color1[1]) * ratio)
            b = int(color1[2] + (color2[2] - color1[2]) * ratio)
            draw.line([(x, y1), (x, y2)], fill=(r, g, b))
    else:
        for y in range(y1, y2):
            ratio = (y - y1) / max(y2 - y1, 1)
            r = int(color1[0] + (color2[0] - color1[0]) * ratio)
            g = int(color1[1] + (color2[1] - color1[1]) * ratio)
            b = int(color1[2] + (color2[2] - color1[2]) * ratio)
            draw.line([(x1, y), (x2, y)], fill=(r, g, b))


def draw_glow_circle(img, center, radius, color, intensity=0.5):
    """绘制发光圆形装饰"""
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for r in range(radius, 0, -3):
        alpha = int(255 * intensity * (r / radius) ** 0.4 * (1 - r / radius))
        alpha = max(0, min(255, alpha))
        x, y = center
        glow_draw.ellipse([x - r, y - r, x + r, y + r], fill=(*color[:3], alpha))
    return Image.alpha_composite(img.convert("RGBA"), glow)


def draw_rounded_image(base_img, cover_img, position, size, radius):
    """将封面图裁剪为圆角矩形并粘贴到底图（保持原始比例，居中裁剪填充）"""
    cover = cover_img.copy()
    target_w, target_h = size
    src_w, src_h = cover.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    cover = cover.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    cover = cover.crop((left, top, left + target_w, top + target_h))
    mask = Image.new("L", size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, size[0], size[1]], radius=radius, fill=255)
    cover_rgba = cover.convert("RGBA")
    cover_rgba.putalpha(mask)
    base_img.paste(cover_rgba, position, cover_rgba)


def draw_text_centered(draw, text, y, font, fill, canvas_width=1080, shadow=True):
    """居中绘制文本"""
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    x = (canvas_width - tw) // 2
    if shadow:
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0))
    draw.text((x, y), text, font=font, fill=fill)
    return bbox[3] - bbox[1]


def draw_text_wrapped_centered(draw, text, y, max_width, font, fill, canvas_width=1080, line_spacing=12):
    """居中自动换行绘制文本"""
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
        tw = bbox[2] - bbox[0]
        x = (canvas_width - tw) // 2
        draw.text((x + 2, y + total_height + 2), line, font=font, fill=(0, 0, 0))
        draw.text((x, y + total_height), line, font=font, fill=fill)
        total_height += (bbox[3] - bbox[1]) + line_spacing

    return total_height


def format_hot_value(count):
    """格式化热度数值（万/亿）"""
    if count >= 100000000:
        return f"{count / 100000000:.1f}亿"
    if count >= 10000:
        return f"{count / 10000:.0f}万"
    if count >= 1000:
        return f"{count // 1000}千"
    return str(count)


def draw_flame(d, cx, cy, size, color):
    """绘制火焰装饰"""
    d.ellipse([cx - size, cy - int(size * 1.5), cx + size, cy + size],
              fill=(color[0], color[1], color[2]))
    inner = int(size * 0.6)
    d.ellipse([cx - inner, cy - int(inner * 1.2), cx + inner, cy + inner],
              fill=(255, 220, 80))
    core = int(size * 0.3)
    d.ellipse([cx - core, cy - core, cx + core, cy + core],
              fill=(255, 255, 220))


def load_cover_image(path):
    """加载封面图"""
    try:
        img = Image.open(path).convert("RGB")
        return img
    except Exception:
        return None

"""
Phase 9: 抓取头条热榜 Top 10（三级 API 容错）
优先: toutiao.com 官方端点
备用: xxapi.cn 第三方聚合
兜底: uapis.cn 多平台聚合
"""
import requests
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_toutiao import (
    ensure_dirs, DATA_DIR, TOP_N,
    TOUTIAO_API_PRIMARY, TOUTIAO_API_FALLBACK, TOUTIAO_API_FALLBACK2
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def fetch_toutiao_official():
    """从头条官方端点获取热榜数据"""
    print(f"[Phase 9] 尝试头条官方: {TOUTIAO_API_PRIMARY}")
    resp = requests.get(TOUTIAO_API_PRIMARY, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    raw_list = data.get("data", [])
    if not raw_list:
        raise ValueError("data 为空")

    items = []
    for i, entry in enumerate(raw_list[:TOP_N], 1):
        # 头条官方 Image 字段是嵌套对象: {url, url_list: [{url}, ...]}
        image_obj = entry.get("Image", {}) or {}
        if isinstance(image_obj, str):
            # 兼容字符串形式
            cover_url_list = [image_obj] if image_obj else []
            first_cover = image_obj
        elif isinstance(image_obj, dict):
            url_list = image_obj.get("url_list", []) or []
            cover_url_list = [u.get("url", "") if isinstance(u, dict) else str(u) for u in url_list]
            first_cover = image_obj.get("url", "") or (cover_url_list[0] if cover_url_list else "")
        else:
            cover_url_list = []
            first_cover = ""

        hot_value = entry.get("HotValue", 0)
        if isinstance(hot_value, str):
            try:
                hot_value = int(hot_value)
            except ValueError:
                hot_value = 0

        # Label: 1=新, 2=热, 3=沸, 4=爆
        label = entry.get("Label", 0)
        if isinstance(label, str):
            label_map_str = {"新": 1, "热": 2, "沸": 3, "爆": 4}
            label = label_map_str.get(label, 0)

        items.append({
            "rank": i,
            "word": entry.get("Title", ""),
            "hot_value": hot_value,
            "label": label,
            "cover_urls": cover_url_list,
            "cover_url": first_cover,
            "video_count": 0,
            "cluster_id": entry.get("ClusterIdStr", ""),
        })

    print(f"  头条官方成功，获取 {len(items)} 条热榜")
    return items


def fetch_xxapi():
    """从 xxapi.cn 获取头条热榜数据"""
    print(f"[Phase 9] 尝试 xxapi: {TOUTIAO_API_FALLBACK}")
    resp = requests.get(TOUTIAO_API_FALLBACK, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 200:
        raise ValueError(f"API 返回异常: code={data.get('code')}")

    raw_list = data.get("data", [])
    if not raw_list:
        raise ValueError("data 为空")

    items = []
    for i, entry in enumerate(raw_list[:TOP_N], 1):
        hot_value = entry.get("hot_value", 0) or entry.get("hot", 0)
        if isinstance(hot_value, str):
            try:
                hot_value = int(hot_value)
            except ValueError:
                hot_value = 0

        items.append({
            "rank": i,
            "word": entry.get("title", "") or entry.get("word", ""),
            "hot_value": hot_value,
            "label": entry.get("label", 0),
            "cover_urls": [],
            "cover_url": entry.get("cover", "") or entry.get("img", "") or "",
            "video_count": entry.get("video_count", 0),
        })

    print(f"  xxapi 成功，获取 {len(items)} 条热榜")
    return items


def fetch_uapis():
    """从 uapis.cn 获取头条热榜数据（兜底方案）"""
    print(f"[Phase 9] 尝试 uapis: {TOUTIAO_API_FALLBACK2}")
    resp = requests.get(TOUTIAO_API_FALLBACK2, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    raw_list = data.get("list", data.get("data", []))
    if not raw_list:
        raise ValueError("list 为空")

    items = []
    for i, entry in enumerate(raw_list[:TOP_N], 1):
        hot_value = entry.get("hot_value", 0) or entry.get("hot", 0)
        if isinstance(hot_value, str):
            try:
                hot_value = int(hot_value)
            except ValueError:
                hot_value = 0

        items.append({
            "rank": i,
            "word": entry.get("title", "") or entry.get("word", ""),
            "hot_value": hot_value,
            "label": entry.get("label", 0),
            "cover_urls": [],
            "cover_url": entry.get("cover", "") or "",
            "video_count": 0,
        })

    print(f"  uapis 成功，获取 {len(items)} 条热榜")
    return items


def fetch_toutiao_hot():
    """依次尝试多个 API"""
    strategies = [
        ("头条官方", fetch_toutiao_official),
        ("xxapi (第三方)", fetch_xxapi),
        ("uapis (兜底)", fetch_uapis),
    ]

    last_error = None
    for name, fetcher in strategies:
        try:
            items = fetcher()
            return items
        except Exception as e:
            last_error = e
            print(f"  {name} 失败: {e}")
            continue

    raise RuntimeError(f"所有 API 均失败，最后错误: {last_error}")


def download_cover_images(items):
    """预下载封面图到本地"""
    print("[Phase 9] 预下载封面图...")
    cover_dir = os.path.join(DATA_DIR, "covers")
    os.makedirs(cover_dir, exist_ok=True)

    for item in items:
        rank = item["rank"]
        cover_urls = item.get("cover_urls", []) or []
        if not cover_urls and item.get("cover_url"):
            cover_urls = [item["cover_url"]]

        downloaded = False
        for j, url in enumerate(cover_urls):
            if not url:
                continue
            try:
                resp = requests.get(url, headers=HEADERS, timeout=10)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    ext = "jpeg"
                    ct = resp.headers.get("content-type", "")
                    if "png" in ct:
                        ext = "png"
                    elif "webp" in ct:
                        ext = "webp"
                    local_path = os.path.join(cover_dir, f"cover_{rank:02d}.{ext}")
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
                    item["local_cover"] = local_path
                    print(f"  #{rank} 封面图已下载 ({len(resp.content)//1024}KB)")
                    downloaded = True
                    break
            except Exception:
                continue

        if not downloaded:
            print(f"  #{rank} 封面图不可用，将使用纯文字卡片")
            item["local_cover"] = ""


def save_items(items):
    """保存数据到 JSON"""
    path = os.path.join(DATA_DIR, "toutiao_hot.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"[Phase 9] 数据已保存: {path}")
    return path


def main():
    ensure_dirs()
    items = fetch_toutiao_hot()

    download_cover_images(items)

    print(f"\n[Phase 9] 头条热榜 Top {len(items)}:")
    for item in items:
        label_map = {1: "新", 2: "热", 3: "沸", 4: "爆"}
        label = label_map.get(item.get("label", 0), "")
        label_str = f" [{label}]" if label else ""
        hot = item["hot_value"]
        hot_str = f"{hot / 10000:.0f}万" if hot >= 10000 else str(hot)
        cover_str = " 有图" if item.get("local_cover") else " 无图"
        print(f"  #{item['rank']:>2}  {item['word']}{label_str}  热度:{hot_str}{cover_str}")

    save_items(items)
    print(f"[Phase 9] 完成! 共获取 {len(items)} 条热榜")
    return items


if __name__ == "__main__":
    main()

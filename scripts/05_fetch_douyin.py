"""
Phase 5: 抓取抖音热搜 Top 10（v2 — 含封面图 + 丰富数据）
优先: xxapi.cn（含封面图、视频数等丰富数据）
备用: iesdouyin.com 官方端点
兜底: uapis.cn 多平台聚合
"""
import requests
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_douyin import (
    ensure_dirs, DATA_DIR, TOP_N,
    DOUYIN_API_PRIMARY, DOUYIN_API_FALLBACK, DOUYIN_API_FALLBACK2
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def fetch_xxapi():
    """从 xxapi.cn 获取热搜数据（数据最丰富：含封面图、视频数、时间戳）"""
    print(f"[Phase 5] 尝试 xxapi: {DOUYIN_API_FALLBACK}")
    resp = requests.get(DOUYIN_API_FALLBACK, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 200:
        raise ValueError(f"API 返回异常: code={data.get('code')}")

    raw_list = data.get("data", [])
    if not raw_list:
        raise ValueError("data 为空")

    items = []
    for i, entry in enumerate(raw_list[:TOP_N], 1):
        word_cover = entry.get("word_cover", {}) or {}
        cover_urls = word_cover.get("url_list", [])

        items.append({
            "rank": i,
            "word": entry.get("word", ""),
            "hot_value": entry.get("hot_value", 0),
            "label": 0,
            "sentence_id": entry.get("sentence_id", ""),
            "event_time": entry.get("event_time", ""),
            "cover_urls": cover_urls,             # 保存所有封面图 URL
            "cover_url": cover_urls[0] if cover_urls else "",
            "video_count": entry.get("video_count", 0),
            "group_id": entry.get("group_id", ""),
        })

    print(f"  xxapi 成功，获取 {len(items)} 条热搜（含封面图）")
    return items


def fetch_iesdouyin():
    """从 iesdouyin.com 官方端点获取热搜数据"""
    print(f"[Phase 5] 尝试 iesdouyin: {DOUYIN_API_PRIMARY}")
    resp = requests.get(DOUYIN_API_PRIMARY, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status_code") != 0:
        raise ValueError(f"API 返回异常: status_code={data.get('status_code')}")

    word_list = data.get("word_list", [])
    if not word_list:
        raise ValueError("word_list 为空")

    items = []
    for i, entry in enumerate(word_list[:TOP_N], 1):
        # iesdouyin 也可能返回 cover 信息
        cover_url = ""
        if entry.get("word_cover"):
            wc = entry["word_cover"]
            urls = wc.get("url_list", []) if isinstance(wc, dict) else []
            cover_url = urls[0] if urls else ""

        items.append({
            "rank": i,
            "word": entry.get("word", ""),
            "hot_value": entry.get("hot_value", 0),
            "label": entry.get("label", 0),
            "sentence_id": entry.get("sentence_id", ""),
            "event_time": entry.get("event_time", ""),
            "cover_urls": [],
            "cover_url": cover_url,
            "video_count": 0,
        })

    print(f"  iesdouyin 成功，获取 {len(items)} 条热搜")
    return items


def fetch_uapis():
    """从 uapis.cn 获取热搜数据（兜底方案）"""
    print(f"[Phase 5] 尝试 uapis: {DOUYIN_API_FALLBACK2}")
    resp = requests.get(DOUYIN_API_FALLBACK2, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    raw_list = data.get("list", [])
    if not raw_list:
        raise ValueError("list 为空")

    items = []
    for i, entry in enumerate(raw_list[:TOP_N], 1):
        extra = entry.get("extra", {}) or {}
        items.append({
            "rank": i,
            "word": entry.get("title", ""),
            "hot_value": entry.get("hot_value", 0),
            "label": extra.get("label", 0),
            "sentence_id": extra.get("sentence_id", ""),
            "event_time": "",
            "cover_urls": [],
            "cover_url": extra.get("cover", ""),
            "video_count": extra.get("video_count", 0),
        })

    print(f"  uapis 成功，获取 {len(items)} 条热搜")
    return items


def fetch_douyin_hot():
    """依次尝试多个 API，优先使用 xxapi（数据最丰富）"""
    strategies = [
        ("xxapi (含封面图)", fetch_xxapi),
        ("iesdouyin (官方)", fetch_iesdouyin),
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
    """预下载封面图到本地，确保图片生成时可用"""
    print("[Phase 5] 预下载封面图...")
    cover_dir = os.path.join(DATA_DIR, "covers")
    os.makedirs(cover_dir, exist_ok=True)

    for item in items:
        rank = item["rank"]
        cover_urls = item.get("cover_urls", []) or []
        if not cover_urls and item.get("cover_url"):
            cover_urls = [item["cover_url"]]

        downloaded = False
        for j, url in enumerate(cover_urls):
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
            except Exception as e:
                continue

        if not downloaded:
            print(f"  #{rank} 封面图不可用，将使用纯文字卡片")
            item["local_cover"] = ""


def save_items(items):
    """保存数据到 JSON"""
    path = os.path.join(DATA_DIR, "douyin_hot.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"[Phase 5] 数据已保存: {path}")
    return path


def main():
    ensure_dirs()
    items = fetch_douyin_hot()

    # 预下载封面图
    download_cover_images(items)

    print(f"\n[Phase 5] 抖音热搜 Top {len(items)}:")
    for item in items:
        label_map = {1: "新", 2: "推荐", 3: "热"}
        label = label_map.get(item.get("label", 0), "")
        label_str = f" [{label}]" if label else ""
        hot = item["hot_value"]
        hot_str = f"{hot / 10000:.0f}万" if hot >= 10000 else str(hot)
        cover_str = " ✓图" if item.get("local_cover") else " ✗无图"
        vid_str = f" ({item.get('video_count', 0)}视频)" if item.get("video_count") else ""
        print(f"  #{item['rank']:>2}  {item['word']}{label_str}  热度:{hot_str}{vid_str}{cover_str}")

    save_items(items)
    print(f"[Phase 5] 完成! 共获取 {len(items)} 条热搜")
    return items


if __name__ == "__main__":
    main()

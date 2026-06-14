"""
Phase 1: 抓取 GitHub Trending Top 10
使用 GitHub API 搜索最近创建的高星项目 + 补充 trending 页面数据
"""
import requests
import json
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ensure_dirs, DATA_DIR, TOP_N

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "GitHub-Trending-Bot/1.0"
}

# 如果有 GitHub token 可以提高 rate limit
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"


def fetch_trending_repos():
    """通过 GitHub Search API 获取近期星数增长最快的项目"""
    # 搜索最近 7 天内创建且星数最高的项目
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    url = f"https://api.github.com/search/repositories"
    params = {
        "q": f"created:>{date_from}",
        "sort": "stars",
        "order": "desc",
        "per_page": TOP_N
    }
    
    print(f"[Phase 1] 正在搜索 GitHub 热门项目 (created after {date_from})...")
    
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    
    repos = []
    for i, item in enumerate(data["items"][:TOP_N], 1):
        repo = {
            "rank": i,
            "name": item["name"],
            "full_name": item["full_name"],
            "owner": item["owner"]["login"],
            "description": item.get("description", "暂无描述") or "暂无描述",
            "stars": item["stargazers_count"],
            "forks": item["forks_count"],
            "language": item.get("language", "Unknown"),
            "url": item["html_url"],
            "homepage": item.get("homepage", ""),
            "topics": item.get("topics", []),
            "created_at": item["created_at"],
            "updated_at": item["updated_at"],
            "owner_avatar": item["owner"]["avatar_url"],
            "open_issues": item["open_issues_count"],
            "watchers": item["watchers_count"],
            "license": item.get("license", {}).get("spdx_id", "N/A") if item.get("license") else "N/A",
        }
        repos.append(repo)
        print(f"  #{i} {repo['full_name']} - ⭐ {repo['stars']} - {repo['language']}")
    
    return repos


def fetch_readme_preview(full_name):
    """获取 README 的前几行作为补充描述"""
    try:
        url = f"https://api.github.com/repos/{full_name}/readme"
        resp = requests.get(url, headers={**HEADERS, "Accept": "application/vnd.github.v3.raw"}, timeout=15)
        if resp.status_code == 200:
            text = resp.text[:2000]
            # 取前 3 段非空行
            lines = [l.strip() for l in text.split('\n') if l.strip() and not l.startswith('#')][:3]
            return ' '.join(lines)[:300]
    except:
        pass
    return ""


def enrich_repos(repos):
    """补充 README 摘要等信息"""
    print("[Phase 1] 正在补充 README 摘要...")
    for repo in repos:
        readme = fetch_readme_preview(repo["full_name"])
        repo["readme_preview"] = readme
    return repos


def save_repos(repos):
    """保存数据到 JSON"""
    path = os.path.join(DATA_DIR, "repos.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(repos, f, ensure_ascii=False, indent=2)
    print(f"[Phase 1] 数据已保存: {path}")
    return path


def main():
    ensure_dirs()
    repos = fetch_trending_repos()
    repos = enrich_repos(repos)
    save_repos(repos)
    print(f"[Phase 1] 完成! 共获取 {len(repos)} 个项目")
    return repos


if __name__ == "__main__":
    main()

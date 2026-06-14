"""
主控脚本: 一键执行完整流水线
Phase 1: 抓取 GitHub Trending → repos.json
Phase 2: 生成科技感卡片图片
Phase 3: 小米 TTS 配音
Phase 4: 合成视频
"""
import subprocess
import sys
import os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

PHASES = [
    ("Phase 1 - GitHub 数据抓取", "01_fetch_github.py"),
    ("Phase 2 - 生成卡片图片", "02_generate_images.py"),
    ("Phase 3 - TTS 配音生成", "03_generate_tts.py"),
    ("Phase 4 - 视频合成", "04_compose_video.py"),
]


def run_phase(name, script):
    print(f"\n{'='*50}")
    print(f"▶ {name}")
    print(f"{'='*50}")
    script_path = os.path.join(SCRIPTS_DIR, script)
    result = subprocess.run([sys.executable, script_path])
    if result.returncode != 0:
        print(f"  ✗ {name} 失败!")
        return False
    print(f"  ✓ {name} 完成")
    return True


def main():
    # 支持从指定 phase 开始: python main.py 3 → 从 Phase 3 开始
    start = 1
    if len(sys.argv) > 1:
        start = int(sys.argv[1])

    print(f"GitHub 热门项目视频生成流水线")
    print(f"从 Phase {start} 开始\n")

    for i, (name, script) in enumerate(PHASES, 1):
        if i < start:
            print(f"  跳过 {name}")
            continue
        if not run_phase(name, script):
            sys.exit(1)

    print(f"\n{'='*50}")
    print("全部完成!")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

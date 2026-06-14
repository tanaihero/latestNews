"""
抖音热搜视频生成主控脚本
Phase 5: 抓取抖音热搜 Top 10
Phase 6: 生成抖音风格卡片图片
Phase 7: 二次元女声 TTS 配音
Phase 8: 带转场特效的视频合成

用法:
  python main_douyin.py        # 从 Phase 5 开始
  python main_douyin.py 7      # 从 Phase 7 开始
"""
import subprocess
import sys
import os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

PHASES = [
    ("Phase 5 - 抖音热搜数据抓取", "05_fetch_douyin.py"),
    ("Phase 6 - 生成抖音风格卡片图片", "06_douyin_generate_images.py"),
    ("Phase 7 - 年轻活泼女声 TTS 配音", "07_douyin_generate_tts.py"),
    ("Phase 8 - 带转场特效视频合成", "08_douyin_compose_video.py"),
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
    # 支持从指定 phase 开始: python main_douyin.py 7 → 从 Phase 7 开始
    start = 5
    if len(sys.argv) > 1:
        start = int(sys.argv[1])

    print(f"抖音热搜视频生成流水线")
    print(f"从 Phase {start} 开始\n")

    for i, (name, script) in enumerate(PHASES, 5):
        if i < start:
            print(f"  跳过 {name}")
            continue
        if not run_phase(name, script):
            sys.exit(1)

    print(f"\n{'='*50}")
    print("抖音热搜视频生成完成!")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

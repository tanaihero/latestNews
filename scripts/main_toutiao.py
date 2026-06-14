"""
头条热榜视频生成主控脚本
Phase 9: 抓取头条热榜 Top 10
Phase 10: 生成头条风格卡片图片
Phase 11: 新闻播报风 TTS 配音
Phase 12: 带转场字幕的视频合成

用法:
  python main_toutiao.py        # 从 Phase 9 开始
  python main_toutiao.py 11     # 从 Phase 11 开始
"""
import subprocess
import sys
import os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

PHASES = [
    ("Phase 9 - 头条热榜数据抓取", "09_fetch_toutiao.py"),
    ("Phase 10 - 生成头条风格卡片图片", "10_toutiao_generate_images.py"),
    ("Phase 11 - 新闻播报风 TTS 配音", "11_toutiao_generate_tts.py"),
    ("Phase 12 - 带字幕转场视频合成", "12_toutiao_compose_video.py"),
]


def run_phase(name, script):
    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"{'='*50}")
    script_path = os.path.join(SCRIPTS_DIR, script)
    result = subprocess.run([sys.executable, script_path])
    if result.returncode != 0:
        print(f"  x {name} 失败!")
        return False
    print(f"  v {name} 完成")
    return True


def main():
    start = 9
    if len(sys.argv) > 1:
        start = int(sys.argv[1])

    print(f"头条热榜视频生成流水线")
    print(f"从 Phase {start} 开始\n")

    for i, (name, script) in enumerate(PHASES, 9):
        if i < start:
            print(f"  跳过 {name}")
            continue
        if not run_phase(name, script):
            sys.exit(1)

    print(f"\n{'='*50}")
    print("头条热榜视频生成完成!")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

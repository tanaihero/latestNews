# latestNews

自动抓取 GitHub 热门项目 / 抖音热搜话题 / 头条热榜，生成竖屏短视频（1080×1920），含卡片图片、AI 配音、字幕和转场特效，可直接发布到 TikTok / 抖音等平台。

## 功能概览

本项目包含三套完全独立的视频生成流水线，互不影响，可独立运行：

### GitHub 热榜视频（Phase 1-4）

抓取 GitHub Trending 本周 Top 10 项目，为每个项目生成**双页卡片**：

- **Page 1** — 项目概览：排名徽章、项目名、作者头像、Stars/Forks/Language 数据卡片、英文描述 + 中文关键词标注、Topics 标签
- **Page 2** — README 中文摘要：结构化展示【项目定位】【文档摘要】【基本信息】，配音采用中文框架 + 英文原文朗读

最终输出约 11 分钟的竖屏视频合集，含 36pt 大字号烧录字幕 + 1 秒淡入淡出转场。

### 抖音热搜视频（Phase 5-8）

抓取抖音热搜 Top 10 话题，生成带真实封面图的卡片 + 年轻活泼女声（XiaoyiNeural）配音，每条话题约 60 秒 5 段落配音，含数据展示和互动引导。最终输出约 11 分钟视频。

### 头条热榜视频（Phase 9-12）

抓取今日头条热榜 Top 10，头条红主题卡片 + 男声新闻播报风（YunxiNeural）配音，每条约 15 秒精简 3 句结构。最终输出约 3 分钟短视频，适合快速浏览。

## 技术特点

- **四阶段流水线架构**：数据抓取 → 图片生成 → 配音生成 → 视频合成，每阶段独立运行，失败可从断点恢复
- **edge-tts 语音合成**：三套流水线分别使用不同语音风格（标准女声 / 活泼女声 / 男声播报）
- **字幕烧录**：ffmpeg drawtext 滤镜直接渲染到视频帧中，兼容性最佳
- **VideoToolbox 硬件加速**：Apple Silicon 上 CPU 占用从 ~790% 降至 ~280%
- **共享工具库**：`scripts/lib/` 封装了绘图、字幕、TTS、视频合成等通用能力，扩展新平台只需对接 API + 品牌视觉
- **非 LLM 中文摘要**：GitHub 版的 README 摘要通过 60+ 技术术语关键词表 + 结构化模板生成，无需调用大语言模型

## 环境依赖

### 系统要求

- macOS（已测试）
- Python 3.9+
- ffmpeg（需含 libass + libfreetype 支持，用于中文字体渲染）

### 安装 ffmpeg

```bash
# macOS: 必须从 homebrew-ffmpeg tap 安装（默认版不含 libass）
brew tap homebrew-ffmpeg/ffmpeg
brew install homebrew-ffmpeg/ffmpeg/ffmpeg

# 验证
ffmpeg -filters | grep subtitles    # 应显示 subtitles 滤镜
ffmpeg -codecs | grep videotoolbox  # 应显示 h264_videotoolbox
```

> **注意**：标准 Homebrew ffmpeg 不包含 libass/libfreetype，无法正确渲染中文字幕。

### Python 依赖

```bash
pip3 install requests Pillow edge-tts
```

## 使用方法

```bash
# 生成 GitHub 热榜视频
python3 scripts/main.py

# 生成抖音热搜视频
python3 scripts/main_douyin.py

# 生成头条热榜视频
python3 scripts/main_toutiao.py

# 从指定阶段开始（跳过已完成的步骤）
python3 scripts/main.py 3          # GitHub: 从 Phase 3（TTS）开始
python3 scripts/main_douyin.py 7   # 抖音: 从 Phase 7（TTS）开始
python3 scripts/main_toutiao.py 11 # 头条: 从 Phase 11（TTS）开始

# 单独运行某个阶段
python3 scripts/01_fetch_github.py
python3 scripts/02_generate_images.py
# ... 以此类推
```

运行完成后，视频文件在输出目录的 `final/` 文件夹中，按日期自动命名。

## 项目结构

```
latestNews/
├── scripts/
│   ├── lib/                         # 跨平台共享工具库
│   │   ├── drawing.py               # PIL 绘图工具（渐变、圆角、文字排版）
│   │   ├── subtitles.py             # SRT 解析 + drawtext 滤镜生成
│   │   ├── tts.py                   # edge-tts 异步封装（含重试）
│   │   └── video.py                 # ffmpeg 视频合成 + VideoToolbox
│   ├── config.py                    # GitHub 版配置
│   ├── config_douyin.py             # 抖音版配置
│   ├── config_toutiao.py            # 头条版配置
│   ├── main.py                      # GitHub 流水线入口
│   ├── main_douyin.py               # 抖音流水线入口
│   ├── main_toutiao.py              # 头条流水线入口
│   ├── 01_fetch_github.py           # Phase 1: GitHub 数据抓取
│   ├── 02_generate_images.py        # Phase 2: 双页卡片 + 中文摘要
│   ├── 03_generate_tts.py           # Phase 3: 双段配音 + 字幕
│   ├── 04_compose_video.py          # Phase 4: 视频合成
│   ├── 05_fetch_douyin.py           # Phase 5: 抖音热搜抓取
│   ├── 06_douyin_generate_images.py # Phase 6: 抖音卡片
│   ├── 07_douyin_generate_tts.py    # Phase 7: 抖音配音
│   ├── 08_douyin_compose_video.py   # Phase 8: 抖音视频合成
│   ├── 09_fetch_toutiao.py          # Phase 9: 头条热榜抓取
│   ├── 10_toutiao_generate_images.py# Phase 10: 头条卡片
│   ├── 11_toutiao_generate_tts.py   # Phase 11: 头条配音
│   └── 12_toutiao_compose_video.py  # Phase 12: 头条视频合成
├── fonts/                           # 自定义字体（可选）
├── templates/                       # 模板资源（可选）
└── README.md
```

每次运行时自动创建以日期命名的输出目录：

```
2026-06-14/                          # GitHub 输出
├── data/repos.json                  # 抓取的仓库数据（含中文摘要）
├── images/                          # 20 张双页卡片 + 封面图
├── audio/                           # 21 段配音音频
├── subtitles/                       # 21 个 SRT 字幕文件
├── clips/                           # 21 个视频片段
└── final/github_top10_2026-06-14.mp4
```

## 输出规格

| 参数 | GitHub 版 | 抖音版 | 头条版 |
|------|-----------|--------|--------|
| 分辨率 | 1080×1920 | 1080×1920 | 1080×1920 |
| 编码 | H.264 (VideoToolbox) + AAC | H.264 (VideoToolbox) + AAC | H.264 (VideoToolbox) + AAC |
| 帧率 | 30fps | 30fps | 30fps |
| 时长 | ~11 分钟 | ~11 分钟 | ~3 分钟 |
| 配音风格 | 标准女声（中英混合） | 年轻活泼女声 | 男声新闻播报 |
| 每项目页数 | 2 页（概览 + 摘要） | 1 页 | 1 页 |
| 字幕 | 36pt, h×0.82 | 28pt, h×0.70 | 28pt, h×0.70 |
| 转场 | 1 秒淡入淡出 | 1 秒淡入淡出 | 1 秒淡入淡出 |

## 配置

各流水线的配置文件相互独立，可单独调整：

- `scripts/config.py` — GitHub 版：TTS 语音（`TTS_VOICE`）、字体路径、视频参数
- `scripts/config_douyin.py` — 抖音版：API 端点（三级容错）、TTS 语音
- `scripts/config_toutiao.py` — 头条版：API 端点（三级容错）、TTS 语音、配音长度控制

更换 TTS 语音只需修改对应 config 中的 `TTS_VOICE` 参数。edge-tts 可用中文语音包括：XiaoxiaoNeural（标准女声）、XiaoyiNeural（年轻女声）、YunjianNeural（男声）、YunxiNeural（年轻男声）等。

## 扩展新平台

共享工具库 `scripts/lib/` 已封装好通用能力，添加新平台只需三步：

1. 新建 `config_{platform}.py`（API、配色、语音）
2. 新建 4 个阶段脚本（Phase N ~ N+3，引用 `lib/` 共享工具）
3. 新建 `main_{platform}.py`（流水线编排）

## 注意事项

- macOS 系统字体 STHeiti Medium 不支持 emoji 渲染，Pillow 绘制时用自绘图形替代
- 字幕使用 PingFang SC 字体，路径在 config 中配置，不同 macOS 版本可能不同
- 如需使用 GitHub API 提高速率限制，可设置环境变量 `GITHUB_TOKEN`
- 抖音和头条的 API 为第三方聚合端点，如遇不可用会自动切换备用源

## License

MIT

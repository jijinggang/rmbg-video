# rmbg-video

使用 rembg AI 模型逐帧去除视频背景，输出带透明通道的 VP8 WebM 视频，保留原音频。

## 系统要求

- Python >= 3.9
- ffmpeg 和 ffprobe 已安装并在 PATH 中

## 安装

```bash
pip install rmbg-video
```

## 使用方式

```bash
# 基本用法
rmbg-video input.mp4
rmbg-video input.mp4 output.webm

# 选择模型
rmbg-video input.mp4 --model u2net

# 调节质量 (0-63，越小越好)
rmbg-video input.mp4 --crf 5

# 输出不含透明通道的普通 WebM
rmbg-video input.mp4 --no-alpha

# 跳过音频处理
rmbg-video input.mp4 --no-audio

# 强制使用 CPU
rmbg-video input.mp4 --no-gpu

# 保留临时文件用于调试
rmbg-video input.mp4 --keep-temp
```

## 选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--model` | `birefnet-general` | rembg 模型名 |
| `--no-alpha-matting` | 否 | 禁用 alpha matting（更快但边缘较硬） |
| `--fg-threshold` | `240` | 前景阈值 |
| `--bg-threshold` | `10` | 背景阈值 |
| `--erode-size` | `10` | 腐蚀尺寸 |
| `--post-process-mask` | 否 | 对遮罩做后处理平滑 |
| `--crf` | `10` | VP8 质量 0-63（越小越好） |
| `--speed` | `good` | 编码速度预设 (good/best/realtime) |
| `--no-alpha` | 否 | 输出不含透明通道的普通 WebM |
| `--no-audio` | 否 | 跳过音频处理 |
| `--keep-temp` | 否 | 保留临时文件用于调试 |
| `--ffmpeg-path` | 自动检测 | ffmpeg 可执行文件路径 |
| `--no-gpu` | 否 | 强制使用 CPU |

## 工作原理

1. 使用 ffmpeg 管道流式解码视频为原始 RGBA 帧
2. 通过 rembg AI 模型逐帧去除背景，应用 alpha matting 平滑边缘
3. 通过 ffmpeg 管道编码为 VP8 + yuva420p 像素格式（支持透明通道）
4. 提取原音频为 Opus 编码，与视频流合并输出最终 WebM

## 许可证

MIT
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

### 命令行

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

# 测试模式：只处理前5帧（快速预览效果）
rmbg-video input.mp4 --test
```

### Web 界面

启动 Web 服务后，团队成员可通过浏览器上传视频、配置参数并预览处理结果。处理任务自动排队，单 GPU 串行执行。

```bash
# 启动 Web 服务
rmbg-video-web

# 或通过 Python 模块启动
python -m rmbg_video.web
```

启动后访问 `http://localhost:7860`，界面功能：

- **上传视频** — 支持 .mp4 / .webm / .mov / .avi / .mkv 格式
- **参数配置** — 所有 CLI 参数均可通过界面调整，测试模式（仅处理前 5 帧）快捷开关位于最前
- **排队处理** — 多人同时提交时自动排队，显示队列状态，单任务串行处理
- **透明预览** — 结果视频以灰色棋盘格为背景预览，直观查看透明通道效果
- **下载结果** — 处理完成后可直接下载 WebM 视频

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
| `--test` | 否 | 测试模式：只处理前5帧 |

## 工作原理

1. 使用 ffmpeg 管道流式解码视频为原始 RGBA 帧
2. 通过 rembg AI 模型逐帧去除背景，应用 alpha matting 平滑边缘
3. 通过 ffmpeg 管道编码为 VP8 + yuva420p 像素格式（支持透明通道）
4. 提取原音频为 Opus 编码，与视频流合并输出最终 WebM

## GPU配置相关

- 用的是cuda12.8版本

- 要卸载 onnxruntime
  - uv python -m pip uninstall onnxruntime onnxruntime-gpu onnxruntime-azure -y
  - uv pip install onnxruntime-gpu  
- 安装cuda
- 安装cudnn
- 根据错误提示把`C:\Program Files\NVIDIA\CUDNN\v9.23\bin\12.9\x64`,`E:\AI\rmbg-video\.venv\Lib\site-packages\tensorrt_libs` 等dll所在路径加入到系统path中
- uv pip install tensorrt-cu12==10.9.0.34

## 许可证

MIT

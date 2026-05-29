## Why

绿幕视频素材需要去除背景生成透明视频，供 Unity 等引擎合成使用。传统色度键（chroma key）边缘生硬且有绿色溢出，`rembg` 库的 AI alpha matting 能产生平滑自然的边缘过渡。需要一个 CLI 工具将 rembg 的图片抠图能力扩展到视频，同时保留原视频音频。

## What Changes

- 新增 `rmbg_video.py` CLI 程序，输入绿幕视频，输出带透明通道的 VP8 WebM 视频
- 逐帧调用 rembg AI 模型（`alpha_matting=True`）进行背景扣除，效果等同 `rembg i -a input.png output.png`
- 使用 ffmpeg 管道实现流式处理：解码 → rembg → VP8 编码，无需 OpenCV
- 提取原视频音频并以 Opus 格式混流回输出视频
- 支持模型选择、alpha matting 参数调节、编码质量控制等命令行选项

## Capabilities

### New Capabilities

- `video-processing`: 视频帧提取与 rembg AI 逐帧抠图，包含 session 复用、alpha matting 配置、进度显示
- `video-encoding`: VP8 透明视频编码（`yuva420p`）与音频保留混流，包含 ffmpeg 管道交互、音频提取重编码

### Modified Capabilities

<!-- 全新项目，无已有 specs -->

## Impact

- 新增文件: `rmbg_video.py`（约 300 行单文件 CLI）
- 新增依赖: `rembg`（含 onnxruntime）、`numpy`、`tqdm`（Python 包）；`ffmpeg`/`ffprobe`（系统工具）
- 无现有代码受影响（全新子项目）
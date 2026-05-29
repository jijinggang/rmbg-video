## Context

绿幕视频素材广泛用于游戏过场、虚拟直播等场景。传统色度键抠图依赖 HSV 色彩空间阈值分割，边缘生硬且无法处理绿色溢出。`rembg` 库利用深度学习模型（U2-Net、IS-Net、BiRefNet 等）做语义级前景/背景分割，配合 alpha matting 可生成平滑的半透明边缘过渡。

本变更将 rembg 的单图抠图能力扩展至视频，通过 ffmpeg 管道实现流式帧处理，输出 Unity 兼容的 VP8 透明 WebM 视频并保留原音轨。用户明确要求：
- 纯 AI 方案（非色度键混合），效果等同 `rembg i -a`
- VP8 编码（非 VP9）
- 单文件实现

## Goals / Non-Goals

**Goals:**
- 从绿幕视频中逐帧去除背景，生成带透明通道的视频
- 抠图质量等同 `rembg i -a input.png output.png`（AI alpha matting）
- 输出格式为 VP8 WebM，Unity VideoPlayer 可识别透明通道
- 原视频音频无损保留（重编码为 Opus）

**Non-Goals:**
- 不支持纯色度键混合方案（用户选择纯 AI）
- 不支持 VP9 编码（用户明确 VP8）
- 不支持实时处理（离线逐帧处理）
- 不支持帧间一致性优化（如光流平滑）
- 不做多进程/多线程并行加速（单帧顺序处理）
- 不做 GUI 界面

## Decisions

### 1. ffmpeg 管道替代 OpenCV

**选型**: 输入视频通过 `ffmpeg -f rawvideo -pix_fmt rgba pipe:stdout` 解码为原始 RGBA 帧，rembg 处理后通过 `ffmpeg -f rawvideo pipe:stdin` 编码为 VP8 WebM。

**替代方案**: 使用 OpenCV `VideoCapture` / `VideoWriter`。但 OpenCV 的 `VideoWriter` 不支持透明通道写入，且需要额外格式转换。

**理由**: ffmpeg 管道方案无需 OpenCV，减少依赖；RGBA 原始数据零拷贝流式传输；完全控制编码参数。

### 2. 解码和编码分两个子进程

**选型**: `ffmpeg 解码 → stdout` 和 `stdin → ffmpeg 编码` 作为两个独立的 `subprocess.Popen` 进程，Python 主循环在中间做 rembg 处理。

**替代方案**: 使用 `ffmpeg-python` 包装库。增加了不必要的依赖，且对透明通道管道的支持不如原生子进程可靠。

**理由**: 两个独立进程便于错误隔离；可分别配置解码和编码参数；`stdin/stdout` 管道是 ffmpeg 标准用法。

### 3. 音频提取后混流

**选型**: 先提取音频为 Opus 临时文件（`ffmpeg -vn -c:a libopus`），视频处理完成后再混流（`-c:v copy -c:a copy -map`）。

**替代方案**: 在视频编码时同时输入音频流。需要 `-map` 精确指定流映射，一旦出错整个处理失败。

**理由**: 分步处理解耦音视频流程，任一阶段失败不相互影响；混流使用 `-c copy` 零开销。

### 4. 单 session 复用

**选型**: 在处理循环前创建 `new_session(model_name)`，所有帧共享。

**理由**: ONNX 模型文件 ~179MB，每次重新加载会消耗数秒，在千帧视频中会累积成巨大开销。session 复用是最关键的优化。

### 5. 默认模型 `isnet-general-use`

**选型**: IS-Net 通用模型作为默认，支持 `--model` 覆盖。

**替代方案**: BiRefNet（质量最高但慢）、U2-Net（通用但边缘不如 IS-Net）。

**理由**: IS-Net 在绿幕场景的质量/速度平衡最好。BiRefNet ~699MB 下载/加载成本高；U2-Net 边缘不如 IS-Net 精细。

### 测试策略

- 测试文件路径: `tests/test_rmbg_video.py`
- 策略:
  - **单元测试**: mock `subprocess.Popen` 和 `rembg.remove`，验证管道构建、参数传递、临时文件管理
  - **集成测试**: 使用小尺寸测试图片（非真实视频）验证 rembg 调用和 ffmpeg 管道联通性
  - 不测试真实视频端到端（依赖外部 ffmpeg 和模型权重，CI 环境不一致）
  - 每个测试函数注释标出对应的 `specs/<capability>/spec.md` 中的 Scenario

## Risks / Trade-offs

- **VP8 alpha 兼容性**: VP8 透明通道不被所有播放器支持（需 Chrome/VLC/Unity）。→ 测试时用 ffprobe 验证 `pix_fmt=yuva420p`，提供 `--no-alpha` 降级选项。
- **处理速度慢**: rembg 单帧约 1-3 秒（CPU），1080p 30fps 视频每分钟需 30-90 分钟。→ 进度条提示预计完成时间；支持 Ctrl+C 中断时保留临时文件。
- **内存占用**: RGBA 原始帧 ~8MB（1080p），流式处理内存恒定。→ 管道方案天然保证。
- **模型未缓存**: 首次运行自动下载 ~179MB 模型文件。→ 启动时提示下载进度。
- **音频同步**: 视频帧计数错误可能导致音画不同步。→ 使用 ffprobe 精确获取帧率（含分数帧率如 30000/1001）；混流时 `-shortest` 截断。
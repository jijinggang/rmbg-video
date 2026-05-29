## ADDED Requirements

### Requirement: 视频帧提取
系统 SHALL 通过 ffprobe 获取输入视频的宽度、高度、帧率和音频流信息。

#### Scenario: 获取标准视频属性
- **WHEN** 输入视频为 1920x1080 @ 30fps 的 MP4 文件
- **THEN** ffprobe 解析返回 width=1920, height=1080, fps=30.0, has_audio=True

#### Scenario: 获取非标准帧率
- **WHEN** 输入视频帧率为 29.97 (30000/1001)
- **THEN** fps 精确计算为 30000/1001 ≈ 29.97，非截断为 29

#### Scenario: 无音频轨道的视频
- **WHEN** 输入视频不包含音频流
- **THEN** has_audio=False，后续跳过音频处理

### Requirement: rembg session 复用
系统 SHALL 在开始处理帧之前创建单个 `new_session`，并在所有帧的处理中复用该 session。

#### Scenario: 多帧共享 session
- **WHEN** 处理 N（N≥2）帧视频
- **THEN** `new_session()` 仅被调用一次，所有帧通过 `remove(frame, session=session)` 传入同一 session 对象

#### Scenario: 显式指定模型名
- **WHEN** 用户指定 `--model birefnet-general`
- **THEN** session 使用 `new_session("birefnet-general")` 创建

#### Scenario: 默认模型
- **WHEN** 用户未指定 `--model`
- **THEN** session 使用 `new_session("isnet-general-use")` 创建

### Requirement: 逐帧 alpha matting 抠图
系统 SHALL 对每一帧调用 `rembg.remove()` 并启用 `alpha_matting=True`，使抠图效果等同 CLI 命令 `rembg i -a input.png output.png`。

#### Scenario: 默认 alpha matting 参数
- **WHEN** 用户未指定 alpha matting 参数
- **THEN** `remove()` 调用传入 `alpha_matting=True`, `alpha_matting_foreground_threshold=240`, `alpha_matting_background_threshold=10`, `alpha_matting_erode_size=10`

#### Scenario: 自定义 alpha matting 参数
- **WHEN** 用户指定 `--fg-threshold 230 --bg-threshold 20 --erode-size 15`
- **THEN** `remove()` 调用传入对应的自定义阈值

#### Scenario: 禁用 alpha matting
- **WHEN** 用户指定 `--no-alpha-matting`
- **THEN** `remove()` 调用传入 `alpha_matting=False`

#### Scenario: 启用后处理遮罩
- **WHEN** 用户指定 `--post-process-mask`
- **THEN** `remove()` 调用传入 `post_process_mask=True`

### Requirement: 管道流式处理
系统 SHALL 使用 ffmpeg 子进程管道解码输入视频为原始 RGBA 帧，处理后通过管道送入 VP8 编码器，避免将所有帧加载到内存。

#### Scenario: 解码管道建立
- **WHEN** 视频处理开始
- **THEN** 创建 ffmpeg 解码子进程，命令包含 `-f rawvideo -pix_fmt rgba pipe:stdout`

#### Scenario: 编码管道建立
- **WHEN** 视频处理开始
- **THEN** 创建 ffmpeg 编码子进程，命令包含 `-f rawvideo -pix_fmt rgba -i pipe:stdin -c:v libvpx -pix_fmt yuva420p`

#### Scenario: 流式帧处理
- **WHEN** 处理第 K 帧（K 为任意帧序号）
- **THEN** 从解码管道读取 K 帧 → rembg 处理 → 写入编码管道，处理过程中不超过 3 帧在内存中

### Requirement: 处理进度显示
系统 SHALL 在处理过程中通过 tqdm 进度条显示当前进度和预计剩余时间。

#### Scenario: 进度条初始化和更新
- **WHEN** 视频包含 100 帧
- **THEN** 进度条显示 total=100，每处理完一帧更新一次，描述为"处理中"

### Requirement: GPU 自动检测
系统 SHALL 自动检测 ONNX Runtime 可用的 GPU 加速（CUDA/TensorRT），并在不支持时输出提示。

#### Scenario: GPU 可用
- **WHEN** ONNX Runtime 检测到 CUDAExecutionProvider
- **THEN** 使用 GPU 加速，不输出警告

#### Scenario: 仅 CPU
- **WHEN** ONNX Runtime 仅有 CPUExecutionProvider
- **THEN** 输出提示 "未检测到 GPU，使用 CPU 处理（较慢）"

#### Scenario: 强制使用 CPU
- **WHEN** 用户指定 `--no-gpu`
- **THEN** 强制使用 CPUExecutionProvider，忽略可用的 GPU
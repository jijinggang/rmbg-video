## ADDED Requirements

### Requirement: 视频上传与参数配置

系统 SHALL 提供 Web 界面让用户上传视频文件并配置所有处理参数。

#### Scenario: 用户上传视频并启动处理
- **WHEN** 用户上传一个视频文件，配置参数（模型、CRF、alpha matting 等）并点击"开始处理"
- **THEN** 系统接受视频文件，将任务加入处理队列，并显示队列位置

#### Scenario: 未上传视频时点击开始处理
- **WHEN** 用户未选择视频文件就点击"开始处理"
- **THEN** 系统显示提示信息，要求先上传视频

#### Scenario: 上传非视频文件
- **WHEN** 用户上传了一个非视频格式的文件（如图片、文档）
- **THEN** 系统拒绝该文件并显示格式不支持的错误提示

#### Scenario: 使用默认参数处理
- **WHEN** 用户只上传视频，不修改任何参数，点击"开始处理"
- **THEN** 系统使用默认参数（birefnet-general 模型、CRF=10、speed=good、启用 alpha channel 等）处理视频

### Requirement: 处理进度显示

系统 SHALL 在处理过程中实时显示进度信息。

#### Scenario: 显示帧处理进度
- **WHEN** 视频正在处理中
- **THEN** 系统显示已处理帧数，进度指示器持续更新

#### Scenario: 处理完成
- **WHEN** 视频处理成功完成
- **THEN** 系统显示"处理完成"状态，并自动展示预览和下载按钮

#### Scenario: 处理过程中发生错误
- **WHEN** 视频处理过程中发生错误（如 ffmpeg 异常、内存不足）
- **THEN** 系统显示具体错误信息，释放资源，并允许用户重试

### Requirement: 透明视频预览

系统 SHALL 在结果展示区提供带棋盘格灰色背景的视频预览，以可视化透明通道效果。

#### Scenario: 展示带透明通道的视频
- **WHEN** 处理完成生成带 alpha 通道的 WebM 视频
- **THEN** 预览区显示灰色棋盘格背景，视频透明区域呈现棋盘格图案

#### Scenario: 展示无透明通道的视频
- **WHEN** 用户选择了 --no-alpha 选项，生成无透明通道的 WebM
- **THEN** 预览区仍使用棋盘格背景，但视频无透明效果（正常展示）

#### Scenario: 用户下载处理结果
- **WHEN** 用户点击下载按钮
- **THEN** 浏览器下载处理完成的 WebM 视频文件

### Requirement: ffmpeg 依赖检查

系统 SHALL 在启动时检查 ffmpeg/ffprobe 可用性。

#### Scenario: ffmpeg 可用
- **WHEN** Web 服务启动时 ffmpeg 和 ffprobe 在系统 PATH 中
- **THEN** 服务正常启动

#### Scenario: ffmpeg 不可用
- **WHEN** Web 服务启动时 ffmpeg 或 ffprobe 不在 PATH 中
- **THEN** 服务启动失败，输出明确的错误信息提示安装 ffmpeg

### Requirement: GPU 检测与提示

系统 SHALL 在启动时检测 GPU 可用性并告知用户。

#### Scenario: GPU 可用
- **WHEN** 服务启动时检测到 CUDA/TensorRT provider
- **THEN** 控制台输出 GPU 型号信息，使用 GPU 加速推理

#### Scenario: 仅 CPU 可用
- **WHEN** 服务启动时未检测到 GPU provider
- **THEN** 控制台输出提示"未检测到 GPU，使用 CPU 处理（较慢）"，使用 CPU 推理

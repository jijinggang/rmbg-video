## ADDED Requirements

### Requirement: VP8 透明视频编码
系统 SHALL 使用 ffmpeg `libvpx` 编码器将处理后的 RGBA 帧编码为 VP8 WebM 视频，像素格式为 `yuva420p`。

#### Scenario: 带透明通道的输出
- **WHEN** 处理完成且未指定 `--no-alpha`
- **THEN** 输出视频的像素格式为 `yuva420p`，ffmpeg 命令包含 `-pix_fmt yuva420p -auto-alt-ref 0`

#### Scenario: 不带透明通道的输出
- **WHEN** 用户指定 `--no-alpha`
- **THEN** 输出视频像素格式为 `yuv420p`，不包含 alpha 通道

#### Scenario: 可配置 CRF 质量
- **WHEN** 用户指定 `--crf 5`
- **THEN** ffmpeg 编码参数包含 `-crf 5`

#### Scenario: 默认 CRF 质量
- **WHEN** 用户未指定 `--crf`
- **THEN** ffmpeg 编码参数使用 `-crf 10`

#### Scenario: 可配置编码速度
- **WHEN** 用户指定 `--speed realtime`
- **THEN** ffmpeg 编码参数包含 `-deadline realtime`

### Requirement: 音频提取
系统 SHALL 从输入视频中提取音轨并重编码为 Opus 格式（WebM 容器兼容），保存为临时文件。

#### Scenario: 有音频的视频
- **WHEN** 输入视频包含音频流且未指定 `--no-audio`
- **THEN** 执行 `ffmpeg -vn -c:a libopus -b:a 96k` 提取音频为 `audio.opus` 临时文件

#### Scenario: 无音频的视频
- **WHEN** 输入视频不包含音频流
- **THEN** 跳过音频提取步骤，直接输出纯视频 WebM

#### Scenario: 跳过音频处理
- **WHEN** 用户指定 `--no-audio`
- **THEN** 跳过音频提取步骤

### Requirement: 音频混流
系统 SHALL 将处理后的视频与提取的音频合并为最终输出文件。

#### Scenario: 混流音视频
- **WHEN** 视频处理完成且存在音频临时文件
- **THEN** 执行 `ffmpeg -c:v copy -c:a copy -map 0:v:0 -map 1:a:0 -shortest` 将音视频合并到最终输出路径

#### Scenario: 无音频时复制视频
- **WHEN** 不存在音频临时文件
- **THEN** 直接将处理后的纯视频文件复制为最终输出

### Requirement: 临时文件管理
系统 SHALL 在 `tempfile.mkdtemp()` 创建的临时目录中存放中间文件，并在程序正常退出时自动清理。

#### Scenario: 正常清理
- **WHEN** 程序正常完成
- **THEN** 临时目录及其所有内容被删除

#### Scenario: Ctrl+C 中断
- **WHEN** 用户按 Ctrl+C 中断处理
- **THEN** 终止所有 ffmpeg 子进程，清理临时目录

#### Scenario: 保留调试文件
- **WHEN** 用户指定 `--keep-temp`
- **THEN** 临时目录不被删除，程序输出临时目录路径

### Requirement: ffmpeg 依赖检查
系统 SHALL 在启动时验证 ffmpeg 和 ffprobe 可执行文件是否可用。

#### Scenario: ffmpeg 在 PATH 中
- **WHEN** `shutil.which("ffmpeg")` 返回有效路径
- **THEN** 正常继续执行

#### Scenario: ffmpeg 不在 PATH 中
- **WHEN** ffmpeg 不在系统 PATH 中
- **THEN** 输出错误信息 "未找到 ffmpeg，请安装 ffmpeg 或使用 --ffmpeg-path 指定路径" 并退出

#### Scenario: 自定义 ffmpeg 路径
- **WHEN** 用户指定 `--ffmpeg-path /custom/ffmpeg`
- **THEN** 使用 `/custom/ffmpeg` 作为 ffmpeg 路径，`/custom/ffprobe` 作为 ffprobe 路径

### Requirement: 默认输出路径
系统 SHALL 在用户未指定输出路径时，基于输入文件名自动生成。

#### Scenario: 自动生成输出路径
- **WHEN** 输入为 `input.mp4` 且用户未指定输出
- **THEN** 输出默认为 `input.webm`

#### Scenario: 保留用户指定输出路径
- **WHEN** 用户指定 `python rmbg_video.py input.mp4 /tmp/out.webm`
- **THEN** 输出写入 `/tmp/out.webm`
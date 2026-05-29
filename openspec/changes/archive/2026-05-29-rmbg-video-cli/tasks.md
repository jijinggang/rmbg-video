## 1. CLI 与 ffmpeg 基础设施

- [x] 1.1 RED: 编写 CLI 参数解析（所有 argparse 参数及其默认值）和 ffmpeg 依赖检查的测试，对应 specs: `video-encoding` ffmpeg依赖检查 / 默认输出路径
- [x] 1.2 GREEN: 实现 `parse_args()` 和 `check_ffmpeg()` 函数，使 1.1 的测试通过

## 2. 视频信息获取与 rembg session

- [x] 2.1 RED: 编写 `get_video_info()`（ffprobe 解析 width/height/fps/audio）和 `new_session()` 创建的测试，对应 specs: `video-processing` 视频帧提取 / rembg session 复用 / GPU自动检测
- [x] 2.2 GREEN: 实现 `get_video_info()` 和 session 创建逻辑，使 2.1 的测试通过

## 3. 核心处理管道

- [x] 3.1 RED: 编写 ffmpeg 解码/编码子进程管道、流式帧传输、rembg 对所有帧批处理（含 alpha matting 参数）和 tqdm 进度的测试，对应 specs: `video-processing` alpha matting抠图 / 管道流式处理 / 处理进度显示
- [x] 3.2 GREEN: 实现 `process_video()` 核心函数，使 3.1 的测试通过

## 4. 编码输出与音频

- [x] 4.1 RED: 编写 VP8 编码参数（yuva420p/auto-alt-ref/crf/deadline）、`extract_audio()`（Opus 提取）和 `mux_audio()`（混流）的测试，对应 specs: `video-encoding` VP8透明视频编码 / 音频提取 / 音频混流
- [x] 4.2 GREEN: 实现编码配置、`extract_audio()`、`mux_audio()` 函数，使 4.1 的测试通过

## 5. main() 编排与错误处理

- [x] 5.1 RED: 编写 `main()` 端到端流程编排、临时文件生命周期（创建/清理/--keep-temp）、KeyboardInterrupt 处理和子进程清理的测试，对应 specs: `video-encoding` 临时文件管理
- [x] 5.2 GREEN: 实现 `main()` 函数和临时文件管理，使 5.1 的测试通过

## Why

当前 Web 端处理完视频后，用户可以下载带透明通道的 WebM 视频，但无法获取扣背景后的单帧图像。许多用户需要序列帧做进一步处理（如导入其他软件编辑）。应在保留现有视频下载的同时，提供序列帧 PNG 的 ZIP 打包下载。

## What Changes

- Web 端处理完成后，额外生成一个包含所有扣背景后 PNG 帧的 ZIP 文件
- 新增 `gr.File` 组件供用户下载该 ZIP
- `process_video()` 新增 `keep_frames` 参数，允许调用方跳过帧目录的自动清理
- CLI 模式行为不变

## Capabilities

### New Capabilities
- `frames-zip-download`: Web 端在处理完成后，将 `frames/dest/` 中的扣背景 PNG 序列帧打包为 ZIP，供用户下载

### Modified Capabilities
<!-- 无现有 capability 被修改 -->

## Impact

- `rmbg_video/cli.py` — `process_video()` 新增 `keep_frames` 参数
- `rmbg_video/web.py` — `process_video_web()`、`handle_submit()`、`create_interface()` 修改
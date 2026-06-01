## Why

用户在 Gradio Web 界面提交视频处理后，无法中途取消任务，只能等待处理完成或强制终止服务器进程。当处理长视频或选择较慢的模型时，这会浪费大量等待时间。需要提供一个取消按钮，让用户可以主动中断正在进行的处理。

## What Changes

- 在 `cli.py` 的 `process_video()` 帧处理循环中加入可选的取消信号检查（`threading.Event`）
- 在 `web.py` 中添加"取消处理"按钮，点击后设置取消信号
- 添加 `ProcessingCancelled` 自定义异常，确保取消时正确清理 ffmpeg 子进程和临时目录
- CLI 模式行为不变（cancel_event 默认为 None）

## Capabilities

### New Capabilities

- `cancel-processing`: Web 界面支持取消正在进行的视频处理任务，包括设置取消信号、检测取消、清理资源和用户通知

### Modified Capabilities

<!-- 无现有 spec 需要修改 -->

## Impact

- `rmbg_video/cli.py`：`process_video()` 新增 `cancel_event` 参数，新增 `ProcessingCancelled` 异常类，新增 `import threading`
- `rmbg_video/web.py`：新增取消按钮 UI、`cancel_processing()` 函数、`_current_cancel_event` 模块变量；修改 `process_video_web()` 和 `handle_submit()` 签名与逻辑
- `rmbg_video/__init__.py`：导出新增的 `ProcessingCancelled`
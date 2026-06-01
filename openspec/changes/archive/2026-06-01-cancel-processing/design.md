## Context

当前 `rmbg_video/web.py` 的 Gradio 界面仅有"开始处理"按钮，用户提交后无法取消。`cli.py` 的 `process_video()` 帧循环会持续运行直到完成或进程被杀死。需要在不影响 CLI 模式的前提下，为 Web 界面添加可中断的处理机制。

约束：
- Gradio 5.x，`submit_btn.click()` 已设置 `concurrency_limit=1`
- `process_video()` 内部使用 ffmpeg 子进程管道（decoder stdout + encoder stdin）
- `process_video_web()` 的 `finally` 块负责清理临时目录

## Goals / Non-Goals

**Goals:**
- 用户可在 Web 界面点击按钮取消正在进行的视频处理
- 取消后 ffmpeg 子进程被终止，临时目录被清理
- CLI 模式行为不受影响

**Non-Goals:**
- 不支持恢复已取消的任务
- 不支持 CLI 模式的取消（已有 KeyboardInterrupt）
- 不实现实时进度条反馈

## Decisions

### 1. 使用 `threading.Event` 作为取消信号

**选择**：在 `process_video()` 中添加 `cancel_event: threading.Event` 参数，帧循环每轮检查 `is_set()`。

**替代方案及否决理由**：
- **Gradio `cancels=[event]`**：仅标记队列事件为取消，无法中断已运行的同步函数，ffmpeg 子进程会继续运行
- **`gr.Progress` 的取消机制**：需要将 `handle_submit` 改为 generator，侵入性大，且与 `cli.py` 无关
- **进程信号 (SIGINT)**：会杀死整个 Gradio 服务器，而非单个任务

### 2. 自定义 `ProcessingCancelled` 异常

**选择**：定义 `ProcessingCancelled(Exception)`，在检测到取消时抛出。

**理由**：利用现有 `try/finally` 清理链路（`process_video` → `process_video_web` → `handle_submit`），无需额外清理代码。

### 3. 取消按钮使用独立 Gradio 事件

**选择**：`cancel_btn.click(fn=cancel_processing)` 作为独立事件，在 Gradio 队列的另一线程中执行。

**理由**：`submit_btn.click()` 和 `cancel_btn.click()` 是不同的函数事件，Gradio 队列会并发处理，取消处理程序可以立即运行而不等待提交完成。

### 4. 模块级 `_current_cancel_event` 变量

**选择**：在 `web.py` 中使用模块级变量存储当前活动的取消事件。

**理由**：由于 `concurrency_limit=1`，同一时间只有一个处理在进行，无需使用字典或更复杂的数据结构。`handle_submit` 的 `finally` 块保证用完后重置为 `None`。

## Risks / Trade-offs

- **[取消延迟]**：取消信号仅在帧间检查，单帧处理时间（rembg.remove 调用）可能长达 500ms+。对于实时/高速编码场景延迟可接受，无需更细粒度的轮询。
- **[竞态条件]**：`cancel_processing()` 可能在 `finally` 块重置 `_current_cancel_event` 的同时被调用。`Event.set()` 是原子操作，对已丢弃的 Event 对象 set 无害（只是保持 set 状态），下次处理创建新 Event 不受影响。
- **[部分输出]**：取消时编码器可能已写入部分帧数据，输出文件不完整。因为 `handle_submit` 在取消时抛出 `gr.Error`，不会返回不完整的视频路径，所以 UI 不会展示损坏的结果。
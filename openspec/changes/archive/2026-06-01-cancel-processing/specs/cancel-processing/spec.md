## ADDED Requirements

### Requirement: 取消信号传递
系统 SHALL 在 `process_video()` 中接收一个可选的 `cancel_event` 参数（`threading.Event` 类型），在每帧处理前检查该事件是否被设置。

#### Scenario: cancel_event 未设置时正常处理
- **WHEN** `cancel_event` 为 None 或 `is_set()` 返回 False
- **THEN** 帧循环正常继续处理下一帧

#### Scenario: cancel_event 已设置时抛出异常
- **WHEN** `cancel_event.is_set()` 返回 True
- **THEN** 系统 SHALL kill decoder 和 encoder 子进程，关闭管道，并抛出 `ProcessingCancelled` 异常

#### Scenario: CLI 模式兼容
- **WHEN** `process_video()` 未传入 `cancel_event` 参数（默认 None）
- **THEN** 行为与修改前完全一致，正常处理所有帧

### Requirement: 取消按钮
Gradio Web 界面 SHALL 提供"取消处理"按钮，与"开始处理"按钮并排显示。

#### Scenario: 点击取消按钮发送信号
- **WHEN** 用户点击"取消处理"按钮且当前有活动处理
- **THEN** 系统设置 `_current_cancel_event`，导致帧循环检测到取消并终止处理

#### Scenario: 无活动处理时点击取消
- **WHEN** 用户点击"取消处理"按钮但当前没有活动处理
- **THEN** 无操作，不发生错误

### Requirement: 取消后资源清理
取消时系统 SHALL 正确清理所有资源：ffmpeg 子进程、管道和临时目录。

#### Scenario: 取消后 ffmpeg 子进程被终止
- **WHEN** 处理被取消
- **THEN** decoder 和 encoder 子进程被 kill，管道被关闭，`process_video()` 的 finally 块完成等待

#### Scenario: 取消后临时目录被清理
- **WHEN** 处理被取消
- **THEN** `process_video_web()` 的 finally 块执行 `shutil.rmtree(temp_dir)`

### Requirement: 取消后用户通知
取消完成后系统 SHALL 通过 Gradio 错误通知告知用户。

#### Scenario: 取消时显示错误通知
- **WHEN** `handle_submit()` 捕获到 `ProcessingCancelled` 异常
- **THEN** 系统抛出 `gr.Error("处理已取消")`，用户看到红色 toast 通知

#### Scenario: 取消后可开始新处理
- **WHEN** 上次处理被取消且 `handle_submit()` 的 finally 块执行完毕
- **THEN** `_current_cancel_event` 重置为 None，用户可以立即提交新任务
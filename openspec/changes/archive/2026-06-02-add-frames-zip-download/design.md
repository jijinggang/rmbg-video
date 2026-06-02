## Context

当前 `process_video()`（cli.py:205-206）在 finally 块中无条件删除 `frames_dir`，`process_video_web()`（web.py:184-185）的 finally 块也重复此操作。Web 端处理完成后，`handle_submit()` 仅返回视频路径给 `gr.Video` 组件。要提供 ZIP 下载，必须在帧目录被删除前将其打包。

## Goals / Non-Goals

**Goals:**
- Web 端处理完成后，自动生成 `{原视频名}_frames.zip`，内含全部扣背景 PNG 序列帧
- 用户可在 Web UI 直接下载该 ZIP
- CLI 模式行为完全不变

**Non-Goals:**
- 不在 CLI 模式增加 ZIP 导出功能
- 不支持选择性导出部分帧
- 不改变帧文件命名规则（保持 `%08d.png`）

## Decisions

### 1. 在 `process_video()` 增加 `keep_frames` 参数而非在 Web 层重新提取帧

`process_video()` 内部用 ffmpeg 提取帧，rembg 处理后在 finally 中删除 `frames_dir`。如果不在 CLI 函数中拦截，Web 层只能重新提取帧（重复 I/O）。

**选择**：新增 `keep_frames=False` 参数，`True` 时跳过 `shutil.rmtree(frames_dir)`。Web 端调用时传 `keep_frames=True`。

### 2. ZIP 在 `handle_submit()` 中创建，不在 `process_video_web()` 中

`process_video_web()` 的职责是编排视频处理流程，打包 ZIP 属于 UI 层的输出准备，应放在 `handle_submit()` 中完成。这样 `process_video_web()` 只负责透传 `keep_frames`，职责清晰。

### 3. 使用 `gr.File` 而非 `gr.DownloadButton`

`gr.File` 兼容性更广，无需关心 Gradio 版本差异。Gradio 自动为本地文件路径生成下载 URL。

### 4. 使用 `zipfile` 标准库而非 `shutil.make_archive`

`zipfile.ZipFile` 可以精确控制 ZIP 内文件名（只存文件名不带路径前缀），避免 `shutil.make_archive` 包含多余的目录层级。

## Risks / Trade-offs

- **磁盘占用**: 保留帧文件直到处理完成并打包 ZIP → 帧文件本身已在磁盘上（处理需要），打包 ZIP 只是多存一份压缩副本。处理完成后立即清理，影响可忽略。
- **取消处理中途**: 用户取消后 `ProcessingCancelled` 异常会导致 `process_video()` 的 finally 块执行。若 `keep_frames=True`，不完整帧会残留 → finally 块在取消时仍执行 `rmtree`，因为取消走的也是 finally 路径，`keep_frames=True` 只是跳过删除，不完整的帧目录会被 `handle_submit()` 的 finally 清理。
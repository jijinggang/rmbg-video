## 1. CLI: process_video() keep_frames 参数

- [x] 1.1 RED: 编写 `test_process_video_keep_frames_true` — 验证 `keep_frames=True` 时 `frames_dir` 不被删除（`tests/test_rmbg_video.py`）
- [x] 1.2 GREEN: 在 `process_video()` 新增 `keep_frames=False` 参数，`True` 时 finally 块跳过 `shutil.rmtree(frames_dir)`（`rmbg_video/cli.py:118`）
- [x] 1.3 REFACTOR: 从 `process_video_web()` 的 finally 块中移除冗余的 `shutil.rmtree(frames_dir)` 调用（`rmbg_video/web.py:184-185`），因为清理职责已由 `process_video()` 统一管理

## 2. Web: process_video_web() 透传 keep_frames

- [x] 2.1 RED: 编写 `test_process_video_web_keep_frames_true` — 验证 `keep_frames=True` 正确透传至 `cli_process_video()`（`tests/test_web.py`）
- [x] 2.2 GREEN: 在 `process_video_web()` 新增 `keep_frames=False` 参数，透传给 `cli_process_video(..., keep_frames=keep_frames)`（`rmbg_video/web.py:128`）

## 3. Web: handle_submit() ZIP 生成与双输出

- [x] 3.1 RED: 编写 `test_handle_submit_generates_zip` — 验证处理完成后生成 `{原视频名}_frames.zip`，内含正确数量的 PNG 帧（`tests/test_web.py`）
- [x] 3.2 RED: 编写 `test_handle_submit_cleans_frames_after_zip` — 验证 ZIP 生成后 `frames_dir` 被清理（`tests/test_web.py`）
- [x] 3.3 GREEN: 在 `handle_submit()` 中：传递 `keep_frames=True`、用 `zipfile` 将 `frames/dest/` 打包为 ZIP、返回 `(video_path, zip_path)` 元组、打包后清理 `frames_dir` 和 `temp_dir`（`rmbg_video/web.py:194`）

## 4. Web: UI 组件

- [x] 4.1 RED: 编写 `test_interface_has_zip_file_output` — 验证界面包含 `gr.File` 组件（`tests/test_web.py`）
- [x] 4.2 GREEN: 在 `create_interface()` 中新增 `gr.File(label="下载序列帧 (ZIP)")` 组件，更新 `submit_btn.click()` 的 `outputs` 为 `[output_video, zip_output]`（`rmbg_video/web.py:243`）
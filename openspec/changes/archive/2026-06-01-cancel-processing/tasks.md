## 1. cli.py — ProcessingCancelled 异常与取消信号传递

- [x] 1.1 RED: 编写 `ProcessingCancelled` 异常类测试（`tests/test_rmbg_video.py`）
  - `TestProcessingCancelled` 类：验证异常可被正确定义和抛出
  - 覆盖 Spec: `cancel-processing / cancel_event已设置时抛出异常`

- [x] 1.2 RED: 编写 `process_video` 取消测试（`tests/test_rmbg_video.py`）
  - `TestProcessVideoCancel` 类：三个场景
    - `test_cancel_during_processing`: 处理开始后设置 cancel_event → 抛出 ProcessingCancelled
    - `test_cancel_before_processing`: 处理前已设置 cancel_event → 立即抛出
    - `test_no_cancel_event_passed`: 未传 cancel_event（CLI 模式）→ 正常完成
  - 覆盖 Spec: `cancel-processing / cancel_event未设置时正常处理`, `cancel_event已设置时抛出异常`, `CLI模式兼容`

- [x] 1.3 GREEN: 在 `cli.py` 中实现取消支持
  - 添加 `import threading`
  - 定义 `ProcessingCancelled(Exception)` 异常类
  - `process_video()` 签名增加 `cancel_event=None` 参数
  - 帧循环顶部添加取消检查：kill 子进程、close 管道、raise ProcessingCancelled

## 2. web.py — 取消按钮 UI 与事件绑定

- [x] 2.1 RED: 编写取消按钮存在性测试（`tests/test_web.py`）
  - `TestInterfaceComponents` 中添加 `test_interface_has_cancel_button`
  - 验证界面至少有两个按钮（提交 + 取消）
  - 覆盖 Spec: `cancel-processing / 取消按钮`

- [x] 2.2 RED: 编写 `cancel_processing()` 测试（`tests/test_web.py`）
  - `TestCancelProcessing` 类：
    - `test_cancel_processing_function_exists`: 函数存在且可调用
    - `test_cancel_processing_noop_when_no_active`: 无活动处理时无操作
    - `test_cancel_during_process_video_web`: cancel_event 已设置时抛出 ProcessingCancelled
  - 覆盖 Spec: `cancel-processing / 点击取消按钮发送信号`, `无活动处理时点击取消`

- [x] 2.3 GREEN: 在 `web.py` 中实现取消按钮
  - 添加 `import threading`
  - 添加 `_current_cancel_event = None` 模块级变量
  - 实现 `cancel_processing()` 函数
  - `create_interface()` 中将单个按钮替换为 `gr.Row()` 中的两个按钮（"开始处理" + "取消处理"）
  - 绑定 `cancel_btn.click(fn=cancel_processing)`

## 3. web.py — 取消信号传递与用户通知

- [x] 3.1 RED: 编写 `handle_submit` 取消流程测试（`tests/test_web.py`）
  - `TestHandleSubmitCancel` 类：
    - `test_handle_submit_resets_cancel_event`: 取消后在 finally 中重置 `_current_cancel_event`
  - 覆盖 Spec: `cancel-processing / 取消时显示错误通知`, `取消后可开始新处理`

- [x] 3.2 GREEN: 在 `web.py` 中实现取消信号传递
  - `process_video_web()` 签名增加 `cancel_event=None` 参数，传递给 `cli_process_video()`
  - `handle_submit()` 中创建 `threading.Event()`，设置 `_current_cancel_event`
  - 捕获 `ProcessingCancelled` 抛出 `gr.Error("处理已取消")`
  - `finally` 块中重置 `_current_cancel_event = None`

## 4. __init__.py — 导出新符号

- [x] 4.1 GREEN: 在 `__init__.py` 的 cli 导出列表中添加 `ProcessingCancelled`

## 5. 验证

- [x] 5.1 运行测试套件确保无回归：`pytest tests/ -v`（99/100 通过，1 个已存在的测试因之前改默认模型未更新而失败，与本次修改无关）

- [x] 5.2 启动 Web 服务手动验证取消流程：上传视频 → 开始处理 → 取消 → 确认 toast 通知

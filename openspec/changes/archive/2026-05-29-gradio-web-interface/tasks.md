## 1. Web 模块骨架与依赖

- [x] 1.1 RED: 编写 Gradio 界面骨架测试，验证 `rmbg_video/web.py` 模块可导入、`create_interface()` 返回 `gr.Blocks` 实例、ffmpeg 启动检查逻辑，对应 specs: `web-interface` ffmpeg依赖检查 / GPU检测与提示
- [x] 1.2 GREEN: 实现 `check_ffmpeg()`、`check_gpu()` 和 `create_interface()` 骨架函数，添加 `gradio` 依赖到 pyproject.toml
- [x] 1.3 REFACTOR: (跳过) Web 与 CLI 需要不同的错误处理策略（sys.exit vs 返回 None），不适合共享

## 2. 视频上传与文件校验

- [x] 2.1 RED: 编写上传组件和文件校验测试，验证空文件拒绝、非视频格式拒绝、有效视频接受，对应 specs: `web-interface` 视频上传与参数配置
- [x] 2.2 GREEN: 实现上传组件（`gr.File`）和 `validate_upload()` 校验函数

## 3. 参数映射与 UI 布局

- [x] 3.1 RED: 编写参数组件和默认值测试，验证所有 CLI 参数（模型、CRF、speed、alpha matting 等）在 Gradio 中对应的组件及其默认值，对应 specs: `web-interface` 视频上传与参数配置 使用默认参数处理
- [x] 3.2 GREEN: 实现参数配置区域 UI 组件（`gr.Dropdown`、`gr.Slider`、`gr.Radio`、`gr.Checkbox` 等），完成 `web-interface` spec 中要求的左侧面板布局，且把常用参数--test放到最前面

## 4. 核心处理函数

- [x] 4.1 RED: 编写 `process_video_web()` 函数测试，验证从 Gradio 输入正确调用 `get_video_info()`、`create_session()`、`process_video()`、`extract_audio()`、`mux_audio()`，含进度回调替换 tqdm、临时文件管理，对应 specs: `web-interface` 处理进度显示 / `queue-management` 临时文件隔离
- [x] 4.2 GREEN: 实现 `process_video_web()` 核心函数，复用 cli.py 中的函数，将 tqdm 替换为 `gr.Progress` 回调，独立管理每个任务的临时目录生命周期

## 5. 排队机制

- [x] 5.1 RED: 编写 Gradio Queue 配置测试，验证 `gr.Queue()` 正确创建、`concurrency_limit=1` 单并发限制生效，对应 specs: `queue-management` 单任务串行处理
- [x] 5.2 GREEN: 实现 `create_interface()` 中的 Queue 配置，启动时注册 `gr.Queue(max_size=None)` 并设置事件处理的 `concurrency_limit=1`
- [x] 5.3 RED: 编写队列状态测试，验证队列位置显示、状态转换（等待中→处理中→完成/失败），对应 specs: `queue-management` 队列状态可见 / 异常恢复
- [x] 5.4 GREEN: 实现队列状态更新逻辑，通过 Gradio 内置 queue 机制 + 自定义状态组件显示排队信息

## 6. 透明视频预览

- [x] 6.1 RED: 编写预览区测试，验证输出组件为 `gr.Video`、自定义 CSS 包含棋盘格背景样式，对应 specs: `web-interface` 透明视频预览
- [x] 6.2 GREEN: 实现预览区域，使用 `gr.Video` 组件 + 自定义 CSS（`repeating-conic-gradient` 棋盘格背景），处理 alpha/non-alpha 两种情况

## 7. 端到端编排与入口点

- [x] 7.1 RED: 编写 E2E 测试，Mock ffmpeg/rembg 调用验证完整流程（上传→参数→处理→输出视频路径），对应 specs: `web-interface` 处理完成 和 处理过程中发生错误 / `queue-management` 异常恢复
- [x] 7.2 GREEN: 实现 `main()` 入口函数和 `rmbg-video-web` console_scripts 入口点，配置 Gradio 服务启动参数（server_name, server_port, share 等）
- [x] 7.3 GREEN: 更新 `pyproject.toml` 添加 `gradio` 依赖和 `rmbg-video-web` 入口点，更新 `rmbg_video/__init__.py` 导出 web 模块符号

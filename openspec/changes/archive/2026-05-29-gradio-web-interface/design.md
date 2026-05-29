## Context

rmbg-video 是一个单文件 Python CLI 工具（`rmbg_video/cli.py`, ~300 行），功能是接收视频文件，通过 ffmpeg 管道 + rembg AI 模型逐帧移除背景，输出带透明通道的 VP8 WebM。当前没有图形界面，在共享 GPU 服务器上需要 SSH 登录操作。

目标是为其增加 Gradio Web 界面，允许团队多人通过浏览器上传视频、配置参数、查看排队进度、预览和下载结果。

**约束：**
- 不修改 `cli.py`，Web 层作为独立模块复用现有函数
- 单 GPU 串行处理（onnxruntime 独占 GPU 资源）
- 短视频场景（≤10 秒），处理时长通常 30 秒到 2 分钟
- 部署在内部共享服务器，无需用户认证

## Goals / Non-Goals

**Goals:**
- 通过浏览器上传视频并配置所有处理参数
- 多人同时提交时自动排队，显示队列位置
- 处理完成后在浏览器中预览带透明通道的视频（棋盘格背景）
- 提供视频下载链接
- 复用 `cli.py` 中所有核心函数，零侵入

**Non-Goals:**
- 不需要用户认证/登录
- 不需要持久化历史记录（会话级别的临时文件）
- 不需要并发 GPU 处理（保持单任务串行）
- 不需要移动端适配
- 不需要实时预览中间帧

## Decisions

### 决策 1: 使用 Gradio 内置 Queue 机制

**选择**: `gr.Queue()` + `concurrency_limit=1`

**理由**: Gradio 内置队列已经提供了排队 UI（显示队列位置、预计等待时间）、自动状态管理、进度回调支持。设置 `concurrency_limit=1` 确保同一时间只有一个视频在处理，后续请求自动排队。这比自建队列少 200+ 行代码，且 Gradio 的队列 UI 用户友好。

**备选方案**:
- Redis + Celery 任务队列：功能更强但引入额外基础设施，对于内部工具过度设计
- 自定义 in-memory 队列 + 轮询：需要手动管理状态和 UI，代码量大

### 决策 2: CSS 棋盘格背景展示透明视频

**选择**: 在 `<video>` 元素外层使用 CSS `background-image` 绘制灰色棋盘格（`conic-gradient` 或 `repeating-conic-gradient`）

**理由**: Chrome/Edge/Firefox 均支持 VP8 WebM alpha 通道渲染。浏览器会自然地将视频透明区域与 CSS 背景混合显示。只需在 video 容器上设置棋盘格 CSS 背景即可，无需 JavaScript 处理。

**CSS 方案**:
```css
.transparent-preview {
    background-image:
        linear-gradient(45deg, #ccc 25%, transparent 25%),
        linear-gradient(-45deg, #ccc 25%, transparent 25%),
        linear-gradient(45deg, transparent 75%, #ccc 75%),
        linear-gradient(-45deg, transparent 75%, #ccc 75%);
    background-size: 20px 20px;
    background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
}
```

**备选方案**:
- Canvas 逐帧渲染：更灵活但性能和实现复杂度高很多，视频 ≤10 秒不需要
- 转换为 PNG 序列/GIF：丢失视频质量和文件大小不可控

### 决策 3: 新文件 `rmbg_video/web.py` 不修改 `cli.py`

**选择**: 创建独立的 `web.py` 模块，从 `cli.py` import 函数直接使用

**理由**: `cli.py` 中的函数设计良好，接口清晰（`parse_args()`, `get_video_info()`, `create_session()`, `process_video()`, `extract_audio()`, `mux_audio()`）。Web 层只需要调用这些函数，不需要修改其内部实现。

**需适配的点**:
- `parse_args()` 返回 argparse Namespace → Web 层直接构造等价 Namespace 或直接传参
- `process_video()` 的 tqdm 进度条 → 替换为 Gradio 的 `gr.Progress()`
- `main()` 中 `shutil.rmtree` 清理 → Web 层独立管理临时文件生命周期

### 决策 4: UI 布局

**选择**: 单页面布局，左侧参数配置 + 右侧预览/下载

```
┌─────────────────────────────────────────────────┐
│            rmbg-video Web 界面                   │
├──────────────────┬──────────────────────────────┤
│  上传视频        │                              │
│  [拖拽或点击]    │    预览区域                    │
│                  │                              │
│  参数配置        │   ┌────────────────────┐    │
│  模型: [select]  │   │ 棋盘格背景 + video  │    │
│  CRF:   [slider] │   │                    │    │
│  Speed: [radio]  │   └────────────────────┘    │
│  Alpha: [check]  │                              │
│  ...             │   [下载结果]                  │
│                  │                              │
│  [开始处理]      │                              │
│  队列位置: 2/5   │                              │
│  处理进度: ████  │                              │
└──────────────────┴──────────────────────────────┘
```

**理由**: 单页面避免多步向导的复杂度；参数区-预览区分列布局信息密度适中。

## Risks / Trade-offs

- **[风险] 大文件上传导致 Gradio 内存压力** → 限制上传文件大小为 500MB，短视频通常远小于此
- **[风险] 用户关闭浏览器后任务丢失** → 无状态设计，无历史记录需求，可接受
- **[风险] ffmpeg 子进程异常退出未清理** → finally 块 + `shutil.rmtree` 确保临时文件清理
- **[取舍] 不支持 Safari（WebM alpha 兼容性差）** → 团队内部工具，Chrome/Edge 为主，可接受

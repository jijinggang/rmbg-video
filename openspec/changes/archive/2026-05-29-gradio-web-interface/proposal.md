## Why

当前 rmbg-video 只有命令行接口，在共享 GPU 服务器上使用时，每个用户都需要 SSH 登录并手动执行命令。团队需要一个通过浏览器即可访问的 Web 界面，且由于单 GPU 一次只能处理一个视频，必须有排队机制避免资源争抢。

## What Changes

- 新增 Gradio Web 界面，提供视频上传、参数配置、处理进度、结果预览/下载的完整流程
- 新增任务排队机制：多人同时提交时自动排队，显示队列位置和等待状态
- 新增透明视频预览：使用 CSS 棋盘格灰色背景展示带透明通道的 WebM 视频
- 现有 CLI 代码不做修改，Web 层作为独立模块复用 `rmbg_video.cli` 中的函数

## Capabilities

### New Capabilities

- `web-interface`: Gradio Web 界面，包含视频上传、参数配置、透明视频预览和下载功能
- `queue-management`: 多用户任务排队管理，单 GPU 串行处理，队列状态可见

### Modified Capabilities

<!-- 无 -- CLI 核心逻辑不变，Web 层仅调用现有函数 -->

## Impact

- **新文件**: `rmbg_video/web.py` (Gradio 界面主体), `tests/test_web.py` (Web 界面测试)
- **新增依赖**: `gradio` (Web UI 框架)
- **现有代码**: `rmbg_video/cli.py` 不变，`rmbg_video/__init__.py` 新增 web 相关导出
- **入口点**: 新增 `rmbg-video-web` console_scripts 入口

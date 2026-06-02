## ADDED Requirements

### Requirement: 处理完成后提供序列帧 ZIP 下载

Web 端视频背景扣除处理完成后，系统 SHALL 将所有扣背景后的 PNG 序列帧打包为一个 ZIP 文件，供用户下载。

#### Scenario: 正常处理完成后生成 ZIP

- **WHEN** 用户上传视频并点击"开始处理"，处理正常完成
- **THEN** 系统在输出目录生成 `{原视频文件名}_frames.zip`，内含全部 `%05d.png` 格式的扣背景帧
- **AND** Web UI 显示该 ZIP 文件的下载入口

#### Scenario: 测试模式下生成 ZIP

- **WHEN** 用户开启测试模式（仅处理 5 帧）并点击"开始处理"
- **THEN** 生成的 ZIP 仅包含 5 张扣背景 PNG 帧

#### Scenario: ZIP 文件名与输入视频关联

- **WHEN** 用户上传 `my_video.mp4` 并处理完成
- **THEN** 生成的 ZIP 文件名为 `my_video_frames.zip`

### Requirement: CLI 模式行为不变

`keep_frames` 参数默认为 `False`，CLI 模式 SHALL 保持现有行为：处理完成后立即删除临时帧目录。

#### Scenario: CLI 模式下帧目录在 finally 中被清理

- **WHEN** 通过 CLI 运行 `rmbg-video input.mp4 --test`
- **THEN** 处理完成后临时帧目录被删除（`process_video()` 的 finally 块执行 `rmtree`）
- **AND** 不生成任何 ZIP 文件

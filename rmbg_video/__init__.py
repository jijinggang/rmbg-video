"""
rmbg_video - 绿幕视频背景扣除 CLI 工具

使用 rembg AI 模型逐帧去除视频背景，输出带透明通道的 VP8 WebM 视频，保留原音频。
"""

__version__ = "1.0.0"

from rmbg_video.cli import (
    check_ffmpeg,
    create_session,
    extract_audio,
    get_video_info,
    main,
    mux_audio,
    parse_args,
    process_video,
)

from rmbg_video.web import (
    check_ffmpeg_web,
    check_gpu_web,
    process_video_web,
    validate_upload,
    create_interface,
    PARAM_DEFAULTS,
)
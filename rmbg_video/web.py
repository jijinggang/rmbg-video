"""
rmbg_video - Gradio Web 界面

提供浏览器端视频上传、参数配置、排队处理和透明视频预览。
"""
import os
import shutil
import threading

import gradio as gr


def check_ffmpeg_web(ffmpeg_path=None):
    """验证 ffmpeg 和 ffprobe 可用，返回 (ffmpeg, ffprobe) 或 (None, None)。

    与 cli.py 的 check_ffmpeg 不同，此函数不调用 sys.exit，
    而是返回 None 让调用方决定如何处理。
    """
    if ffmpeg_path:
        if not os.path.isfile(ffmpeg_path):
            return None, None
        ffprobe = ffmpeg_path.replace("ffmpeg", "ffprobe")
        return ffmpeg_path, ffprobe

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg:
        return None, None
    return ffmpeg, ffprobe


def check_gpu_web():
    """检测 GPU 可用性，返回 (has_gpu, providers)。

    与 cli.py 的 create_session 中的逻辑相同，但独立实现，
    不依赖 argparse Namespace。
    """
    import onnxruntime as ort
    providers = ort.get_available_providers()
    has_gpu = any("CUDA" in p or "TensorRT" in p for p in providers)
    return has_gpu, providers


VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v", ".flv", ".wmv"}

PARAM_DEFAULTS = {
    "model": "bria-rmbg",
    "alpha_matting": True,
    "fg_threshold": 240,
    "bg_threshold": 10,
    "erode_size": 10,
    "post_process_mask": False,
    "crf": 10,
    "speed": "best",
    "alpha": True,
    "no_audio": False,
    "test": False,
    "no_gpu": False,
}

# 当前活动的取消事件和所属会话，由 handle_submit 设置，cancel_processing 消费。
# concurrency_limit=1 确保同一时间只有一个处理在进行。
_current_cancel_event = None   # threading.Event | None
_active_session_hash = None     # str | None


def validate_upload(file_path):
    """校验上传文件是否有效。返回 True/False。"""
    if not file_path:
        return False
    if not os.path.isfile(file_path):
        return False
    ext = os.path.splitext(file_path)[1].lower()
    return ext in VIDEO_EXTENSIONS


def cancel_processing(request: gr.Request):
    """取消按钮事件处理：仅允许创建任务的会话取消自己的处理。"""
    global _current_cancel_event, _active_session_hash
    if _current_cancel_event is None:
        gr.Info("当前没有正在进行的处理")
    elif _active_session_hash == request.session_hash:
        _current_cancel_event.set()
        gr.Info("取消信号已发送，正在终止处理...")


CHECKERBOARD_CSS = """
.checkerboard-bg,
.checkerboard-bg > *,
.checkerboard-bg video {
    background-color: transparent !important;
}
.checkerboard-bg {
    background-color: #808080 !important;
    background-image:
        linear-gradient(45deg, #b0b0b0 25%, transparent 25%),
        linear-gradient(-45deg, #b0b0b0 25%, transparent 25%),
        linear-gradient(45deg, transparent 75%, #b0b0b0 75%),
        linear-gradient(-45deg, transparent 75%, #b0b0b0 75%);
    background-size: 20px 20px;
    background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
}
.checkerboard-bg video {
    max-width: 600px;
    max-height: 600px;
    object-fit: contain;
}
"""

# 模型 session 缓存：{(model, no_gpu): session}
_session_cache = {}


def get_or_create_session(model="birefnet-general", no_gpu=False):
    """获取或创建 rembg session，缓存复用避免重复加载模型。"""
    import argparse
    from rmbg_video.cli import create_session

    cache_key = (model, no_gpu)
    if cache_key not in _session_cache:
        print(f"加载模型 '{model}'（首次加载约需数秒）...")
        args = argparse.Namespace(model=model, no_gpu=no_gpu)
        _session_cache[cache_key] = create_session(args)
        print(f"模型 '{model}' 加载完成，已缓存")
    return _session_cache[cache_key]


def process_video_web(input_video, ffmpeg_path, ffprobe_path, output_video,
                       temp_dir, model="birefnet-general", alpha_matting=True,
                       fg_threshold=240, bg_threshold=10, erode_size=10,
                       post_process_mask=False, crf=10, speed="best",
                       alpha=True, no_audio=False, test=False, no_gpu=False,
                       cancel_event=None, progress=None, keep_frames=False):
    """Web 端视频处理入口：编排 CLI 函数调用并管理临时文件。

    复用 rmbg_video.cli 中的 get_video_info, create_session, process_video,
    extract_audio, mux_audio。独立管理每个任务的临时目录。
    """
    from rmbg_video.cli import get_video_info
    from rmbg_video.cli import process_video as cli_process_video
    from rmbg_video.cli import extract_audio, mux_audio

    width, height, fps, has_audio = get_video_info(ffprobe_path, input_video)

    session = get_or_create_session(model=model, no_gpu=no_gpu)

    os.makedirs(os.path.dirname(output_video) or ".", exist_ok=True)

    try:
        audio_path = None
        if has_audio and not no_audio:
            audio_path = extract_audio(ffmpeg_path, input_video, temp_dir)

        temp_video = os.path.join(temp_dir, "video_raw.webm")
        max_frames = 5 if test else None

        cli_process_video(
            ffmpeg_path, input_video, temp_video, session,
            width, height, fps, temp_dir,
            alpha_matting=alpha_matting,
            post_process_mask=post_process_mask,
            fg_threshold=fg_threshold,
            bg_threshold=bg_threshold,
            erode_size=erode_size,
            crf=crf,
            speed=speed,
            alpha=alpha,
            max_frames=max_frames,
            cancel_event=cancel_event,
            keep_frames=keep_frames,
        )

        if audio_path:
            mux_audio(ffmpeg_path, temp_video, audio_path, output_video)
        else:
            import shutil
            shutil.copy2(temp_video, output_video)

        return output_video

    except Exception:
        raise
    finally:
        import shutil
        video_raw = os.path.join(temp_dir, "video_raw.webm")
        if os.path.isfile(video_raw):
            os.remove(video_raw)
        audio_opus = os.path.join(temp_dir, "audio.opus")
        if os.path.isfile(audio_opus):
            os.remove(audio_opus)


def handle_submit(input_video, model, alpha_matting, fg_threshold,
                  bg_threshold, erode_size, post_process_mask,
                  crf, no_alpha, no_audio, test_mode, no_gpu,
                  request: gr.Request):
    """Gradio 事件处理器：校验输入、准备路径、调用 process_video_web。"""
    import tempfile
    import gradio as gr
    from rmbg_video.cli import ProcessingCancelled

    global _current_cancel_event, _active_session_hash

    cancel_event = threading.Event()
    _current_cancel_event = cancel_event
    _active_session_hash = request.session_hash

    try:
        if not validate_upload(input_video):
            raise gr.Error("请先上传一个有效的视频文件（支持 .mp4, .webm, .mov, .avi, .mkv）")

        ffmpeg_path, ffprobe_path = check_ffmpeg_web()
        if not ffmpeg_path:
            raise gr.Error("服务器未找到 ffmpeg，请联系管理员")

        temp_dir = tempfile.mkdtemp(prefix="rmbg_")
        output_path = os.path.join(
            temp_dir,
            os.path.splitext(os.path.basename(input_video))[0] + ".webm",
        )

        result = process_video_web(
            input_video, ffmpeg_path, ffprobe_path, output_path,
            temp_dir,
            model=model, alpha_matting=alpha_matting,
            fg_threshold=fg_threshold, bg_threshold=bg_threshold,
            erode_size=erode_size, post_process_mask=post_process_mask,
            crf=crf, speed="best", alpha=not no_alpha, no_audio=no_audio,
            test=test_mode, no_gpu=no_gpu,
            cancel_event=cancel_event,
            keep_frames=True,
        )

        import zipfile
        dest_dir = os.path.join(temp_dir, "frames", "dest")
        zip_name = os.path.splitext(os.path.basename(input_video))[0] + "_frames.zip"
        zip_path = os.path.join(temp_dir, zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in sorted(os.listdir(dest_dir)):
                zf.write(os.path.join(dest_dir, fname), fname)

        shutil.rmtree(os.path.join(temp_dir, "frames"), ignore_errors=True)

        return result, zip_path, result

    except ProcessingCancelled:
        raise gr.Error("处理已取消")

    finally:
        _current_cancel_event = None
        _active_session_hash = None


def create_interface():
    """创建 Gradio Blocks 界面，含排队机制和透明视频预览。"""
    import gradio as gr

    with gr.Blocks(title="rmbg-video") as demo:
        gr.Markdown("# rmbg-video Web 界面")

        with gr.Row():
            # 左侧：上传与参数
            with gr.Column(scale=1):
                video_input = gr.File(
                    label="上传视频",
                    file_types=[".mp4", ".webm", ".mov", ".avi", ".mkv"],
                )

                with gr.Accordion("常用选项", open=True):
                    test_mode = gr.Checkbox(
                        label="测试模式（仅处理前 5 帧）",
                        value=PARAM_DEFAULTS["test"],
                    )


                with gr.Accordion("视频编码", open=False):
                    crf = gr.Slider(
                        label="CRF 质量 (0-63)",
                        minimum=0, maximum=63, step=1,
                        value=PARAM_DEFAULTS["crf"],
                    )
                    no_alpha = gr.Checkbox(
                        label="禁用透明通道",
                        value=not PARAM_DEFAULTS["alpha"],
                    )
                    no_audio = gr.Checkbox(
                        label="跳过音频",
                        value=PARAM_DEFAULTS["no_audio"],
                    )

                with gr.Accordion("Alpha Matting 参数", open=False):
                    alpha_matting = gr.Checkbox(
                        label="启用 Alpha Matting",
                        value=PARAM_DEFAULTS["alpha_matting"],
                    )
                    fg_threshold = gr.Slider(
                        label="前景阈值",
                        minimum=0, maximum=255, step=1,
                        value=PARAM_DEFAULTS["fg_threshold"],
                    )
                    bg_threshold = gr.Slider(
                        label="背景阈值",
                        minimum=0, maximum=255, step=1,
                        value=PARAM_DEFAULTS["bg_threshold"],
                    )
                    erode_size = gr.Slider(
                        label="腐蚀尺寸",
                        minimum=0, maximum=50, step=1,
                        value=PARAM_DEFAULTS["erode_size"],
                    )
                    post_process_mask = gr.Checkbox(
                        label="后处理遮罩平滑",
                        value=PARAM_DEFAULTS["post_process_mask"],
                    )

                with gr.Accordion("高级选项", open=False):
                    model = gr.Dropdown(
                        label="模型",
                        choices=["bria-rmbg", "birefnet-general", "u2net", "isnet-general-use", "sam"],
                        value=PARAM_DEFAULTS["model"],
                    )
                    no_gpu = gr.Checkbox(
                        label="强制使用 CPU",
                        value=PARAM_DEFAULTS["no_gpu"],
                    )

                submit_btn = gr.Button("开始处理", variant="primary")
                cancel_btn = gr.Button("取消处理", variant="stop")

            # 右侧：预览与下载
            with gr.Column(scale=1):
                output_video = gr.Video(
                    label="处理结果",
                    elem_classes=["checkerboard-bg"],
                )
                video_state = gr.State()
                download_btn = gr.DownloadButton("下载视频")
                zip_output = gr.File(label="下载序列帧 (ZIP)")

        # 事件绑定：按钮点击 → 处理视频（concurrency_limit=1 确保排队）
        submit_btn.click(
            fn=handle_submit,
            inputs=[video_input, model, alpha_matting, fg_threshold,
                    bg_threshold, erode_size, post_process_mask,
                    crf, no_alpha, no_audio, test_mode, no_gpu],
            outputs=[output_video, zip_output, video_state],
            concurrency_limit=1,
        )

        # 下载视频按钮：从 State 读取视频路径触发下载
        def download_video(video_path):
            if video_path and os.path.isfile(video_path):
                return video_path
            return None

        download_btn.click(
            fn=download_video,
            inputs=video_state,
            outputs=download_btn,
        )

        # 取消按钮：设置取消信号，在独立线程中运行
        cancel_btn.click(
            fn=cancel_processing,
            inputs=[],
            outputs=[],
        )

    demo.enable_queue = True
    return demo


def main():
    """Gradio Web 服务入口。启动时检查依赖，配置并启动服务。"""
    import sys

    # 检查 ffmpeg
    ffmpeg, _ffprobe = check_ffmpeg_web()
    if not ffmpeg:
        print("错误: 未找到 ffmpeg，请安装 ffmpeg 后重试", file=sys.stderr)
        sys.exit(1)

    # 检查 GPU
    has_gpu, _providers = check_gpu_web()
    if has_gpu:
        print("检测到 GPU，使用 GPU 加速推理")
    else:
        print("未检测到 GPU，使用 CPU 处理（较慢）")

    # 路径自动检测（通过 --ffmpeg-path 参数支持自定义路径暂不在 web main 中暴露，
    # 但可在 process_video_web 中通过队列传入自定义参数）
    # Web 模式下 ffmpeg_path 固定为 check_ffmpeg_web 返回的路径
    # process_video_web 每次调用时接受 ffmpeg_path 参数

    demo = create_interface()
    demo.queue(max_size=None)
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        css=CHECKERBOARD_CSS,
    )


if __name__ == "__main__":
    main()

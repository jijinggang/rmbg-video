"""
rmbg_video - 绿幕视频背景扣除 CLI 工具

使用 rembg AI 模型逐帧去除视频背景，输出带透明通道的 VP8 WebM 视频，保留原音频。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys


def parse_args(argv=None):
    """解析 CLI 参数"""
    parser = argparse.ArgumentParser(
        prog="rmbg_video",
        description="使用 rembg AI 模型去除视频背景，输出 VP8 透明 WebM",
    )
    parser.add_argument("input", help="输入视频路径")
    parser.add_argument("output", nargs="?", default=None, help="输出视频路径（默认：输入文件名 + .webm）")

    parser.add_argument("--model", default="birefnet-general",
                        help="rembg 模型名（默认: birefnet-general）")
    parser.add_argument("--no-alpha-matting", action="store_true",
                        help="禁用 alpha matting（更快但边缘较硬）")
    parser.add_argument("--fg-threshold", type=int, default=240,
                        help="前景阈值（默认: 240）")
    parser.add_argument("--bg-threshold", type=int, default=10,
                        help="背景阈值（默认: 10）")
    parser.add_argument("--erode-size", type=int, default=10,
                        help="腐蚀尺寸（默认: 10）")
    parser.add_argument("--post-process-mask", action="store_true",
                        help="对遮罩做后处理平滑")

    parser.add_argument("--crf", type=int, default=10,
                        help="VP8 质量 0-63（默认: 10，越小越好）")
    parser.add_argument("--speed", default="best", choices=("good", "best", "realtime"),
                        help="编码速度预设（默认: best）")
    parser.add_argument("--no-alpha", action="store_true",
                        help="输出不含透明通道的普通 WebM")
    parser.add_argument("--no-audio", action="store_true",
                        help="跳过音频处理")

    parser.add_argument("--keep-temp", action="store_true",
                        help="保留临时文件用于调试")
    parser.add_argument("--ffmpeg-path", default=None,
                        help="ffmpeg 可执行文件路径")
    parser.add_argument("--no-gpu", action="store_true",
                        help="强制使用 CPU")
    parser.add_argument("--test", action="store_true",
                        help="测试模式：只处理前5帧")

    return parser.parse_args(argv)


def check_ffmpeg(ffmpeg_path):
    """验证 ffmpeg 和 ffprobe 可用，返回 (ffmpeg, ffprobe) 路径"""
    if ffmpeg_path:
        ffmpeg = ffmpeg_path
        ffprobe = ffmpeg_path.replace("ffmpeg", "ffprobe")
        if not os.path.isfile(ffmpeg):
            print(f"错误: 指定的 ffmpeg 路径不存在: {ffmpeg}", file=sys.stderr)
            sys.exit(1)
    else:
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if not ffmpeg:
            print("未找到 ffmpeg，请安装 ffmpeg 或使用 --ffmpeg-path 指定路径", file=sys.stderr)
            sys.exit(1)
    return ffmpeg, ffprobe


def get_video_info(ffprobe_path, input_video):
    """通过 ffprobe 获取视频 width, height, fps, has_audio"""
    cmd = [
        ffprobe_path, "-v", "quiet", "-print_format", "json",
        "-show_streams", input_video,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(result.stdout)

    width = height = fps = 0
    has_audio = False
    for stream in info.get("streams", []):
        if stream["codec_type"] == "video":
            width = int(stream["width"])
            height = int(stream["height"])
            fps_str = stream.get("avg_frame_rate", stream.get("r_frame_rate", "0/1"))
            num, den = fps_str.split("/")
            fps = float(num) / float(den)
        elif stream["codec_type"] == "audio":
            has_audio = True

    return width, height, fps, has_audio


def create_session(args):
    """创建 rembg session，处理 GPU 检测和模型选择"""
    import onnxruntime as ort

    providers = ort.get_available_providers()
    has_gpu = any("CUDA" in p or "TensorRT" in p for p in providers)

    if args.no_gpu:
        providers = ["CPUExecutionProvider"]
    elif not has_gpu:
        print("未检测到 GPU，使用 CPU 处理（较慢）")

    import rembg
    return rembg.new_session(args.model, providers=providers)


class ProcessingCancelled(Exception):
    """用户取消视频处理时抛出，确保 finally 块完成资源清理。"""


def process_video(ffmpeg_path, input_video, output_video, session,
                  width, height, fps, temp_dir, alpha_matting=True,
                  post_process_mask=False,
                  fg_threshold=240, bg_threshold=10, erode_size=10,
                  crf=10, speed="best", alpha=True, max_frames=None,
                  cancel_event=None):
    """帧提取到磁盘 → rembg 批量处理 → ffmpeg 合成视频"""
    import rembg
    from tqdm import tqdm

    if cancel_event is not None and cancel_event.is_set():
        raise ProcessingCancelled()

    frames_dir = os.path.join(temp_dir, "frames")
    src_dir = os.path.join(frames_dir, "src")
    dest_dir = os.path.join(frames_dir, "dest")
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(dest_dir, exist_ok=True)

    frameno = 0

    try:
        # 阶段 1：ffmpeg 提取帧到 src/ 目录
        extract_cmd = [
            ffmpeg_path, "-y",
            "-i", input_video,
            "-r", str(fps),
            "-s", f"{width}x{height}",
        ]
        if max_frames is not None:
            extract_cmd += ["-vframes", str(max_frames)]
        extract_cmd.append(os.path.join(src_dir, "%08d.png"))

        subprocess.run(extract_cmd, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 阶段 2：rembg 逐张处理 src/ → dest/
        frame_files = sorted(f for f in os.listdir(src_dir) if f.endswith(".png"))
        pbar = tqdm(frame_files, unit="帧", desc="处理中")

        try:
            for fname in pbar:
                if cancel_event is not None and cancel_event.is_set():
                    print("检测到取消信号，正在终止处理...")
                    raise ProcessingCancelled()

                src_path = os.path.join(src_dir, fname)
                dest_path = os.path.join(dest_dir, fname)

                with open(src_path, "rb") as f:
                    frame_bytes = f.read()

                result = rembg.remove(
                    frame_bytes,
                    session=session,
                    alpha_matting=alpha_matting,
                    alpha_matting_foreground_threshold=fg_threshold,
                    alpha_matting_background_threshold=bg_threshold,
                    alpha_matting_erode_size=erode_size,
                    post_process_mask=post_process_mask,
                )

                with open(dest_path, "wb") as f:
                    f.write(result)

                frameno += 1
        finally:
            pbar.close()

        # 阶段 3：ffmpeg 从 dest/ 合成视频
        if frameno > 0:
            pix_fmt = "yuva420p" if alpha else "yuv420p"
            encode_cmd = [
                ffmpeg_path, "-y",
                "-r", str(fps),
                "-i", os.path.join(dest_dir, "%08d.png"),
                "-c:v", "libvpx",
                "-pix_fmt", pix_fmt,
                "-auto-alt-ref", "0",
                "-crf", str(crf),
                "-b:v", "0",
                "-deadline", speed,
                output_video,
            ]
            subprocess.run(encode_cmd, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    finally:
        shutil.rmtree(frames_dir, ignore_errors=True)

    print(f"处理完成：{frameno} 帧")


def extract_audio(ffmpeg_path, input_video, temp_dir):
    """从输入视频中提取音频为 Opus 格式。无音轨时返回 None。"""
    audio_path = os.path.join(temp_dir, "audio.opus")
    cmd = [
        ffmpeg_path, "-y",
        "-i", input_video,
        "-vn",
        "-c:a", "libopus",
        "-b:a", "96k",
        audio_path,
    ]
    # 使用 Popen 让 ffmpeg 运行，用 run 等待完成
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    proc.wait()
    if proc.returncode != 0 or not os.path.isfile(audio_path):
        return None
    return audio_path


def mux_audio(ffmpeg_path, video_path, audio_path, output_path):
    """将视频与音频合并为最终 WebM"""
    cmd = [
        ffmpeg_path, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        output_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    """CLI 入口：编排完整处理流程"""
    args = parse_args()
    ffmpeg, ffprobe = check_ffmpeg(args.ffmpeg_path)

    print(f"分析视频: {args.input}")
    width, height, fps, has_audio = get_video_info(ffprobe, args.input)
    print(f"分辨率: {width}x{height}, 帧率: {fps:.2f} fps, "
          f"音频: {'有' if has_audio else '无'}")

    args.output = args.output or os.path.splitext(args.input)[0] + ".webm"
    use_audio = has_audio and not args.no_audio

    print(f"加载模型 '{args.model}'...")
    session = create_session(args)

    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="rmbg_")
    print(f"临时目录: {temp_dir}")

    try:
        # 阶段 1：提取音频
        audio_path = None
        if use_audio:
            print("提取音频...")
            audio_path = extract_audio(ffmpeg, args.input, temp_dir)
            if audio_path:
                print("音频提取完成")
            else:
                print("音频提取失败，输出无音频视频")

        # 阶段 2：处理视频
        print("开始处理视频帧...")
        temp_video = os.path.join(temp_dir, "video_raw.webm")
        process_video(
            ffmpeg, args.input, temp_video, session,
            width, height, fps, temp_dir,
            alpha_matting=not args.no_alpha_matting,
            post_process_mask=args.post_process_mask,
            fg_threshold=args.fg_threshold,
            bg_threshold=args.bg_threshold,
            erode_size=args.erode_size,
            crf=args.crf,
            speed=args.speed,
            alpha=not args.no_alpha,
            max_frames=5 if args.test else None,
        )

        # 阶段 3：混流音频
        if audio_path:
            print("合并音频...")
            mux_audio(ffmpeg, temp_video, audio_path, args.output)
        else:
            import shutil
            shutil.copy2(temp_video, args.output)

        print(f"输出: {args.output}")

    except KeyboardInterrupt:
        print("\n用户中断，正在清理...")
        raise
    finally:
        if not args.keep_temp:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            print(f"临时文件保留在: {temp_dir}")


if __name__ == "__main__":
    main()

import json
import os
import subprocess
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# === Task 1.1: CLI 参数解析 和 ffmpeg 依赖检查 ===
# specs: video-encoding / ffmpeg依赖检查, 默认输出路径

class TestParseArgs:
    """CLI 参数解析测试"""

    def test_default_values(self, monkeypatch):
        """Scenario: 所有参数默认值"""
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4"])
        from rmbg_video import parse_args
        args = parse_args()
        assert args.input == "input.mp4"
        assert args.output is None
        assert args.model == "birefnet-general"
        assert args.no_alpha_matting is False
        assert args.fg_threshold == 240
        assert args.bg_threshold == 10
        assert args.erode_size == 10
        assert args.post_process_mask is False
        assert args.crf == 10
        assert args.speed == "good"
        assert args.keep_temp is False
        assert args.ffmpeg_path is None
        assert args.no_audio is False
        assert args.no_alpha is False
        assert args.no_gpu is False
        assert args.test is False

    def test_output_specified(self, monkeypatch):
        """Scenario: 保留用户指定输出路径"""
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4", "/tmp/out.webm"])
        from rmbg_video import parse_args
        args = parse_args()
        assert args.input == "input.mp4"
        assert args.output == "/tmp/out.webm"

    def test_all_flags_set(self, monkeypatch):
        """Scenario: 所有可选参数显式指定"""
        monkeypatch.setattr(sys, "argv", [
            "rmbg_video.py", "input.mp4",
            "--model", "u2net",
            "--no-alpha-matting",
            "--fg-threshold", "230",
            "--bg-threshold", "20",
            "--erode-size", "15",
            "--post-process-mask",
            "--crf", "5",
            "--speed", "realtime",
            "--keep-temp",
            "--ffmpeg-path", "/custom/ffmpeg",
            "--no-audio",
            "--no-alpha",
            "--no-gpu",
            "--test",
        ])
        from rmbg_video import parse_args
        args = parse_args()
        assert args.model == "u2net"
        assert args.no_alpha_matting is True
        assert args.fg_threshold == 230
        assert args.bg_threshold == 20
        assert args.erode_size == 15
        assert args.post_process_mask is True
        assert args.crf == 5
        assert args.speed == "realtime"
        assert args.keep_temp is True
        assert args.ffmpeg_path == "/custom/ffmpeg"
        assert args.no_audio is True
        assert args.no_alpha is True
        assert args.no_gpu is True
        assert args.test is True


class TestCheckFfmpeg:
    """ffmpeg 依赖检查测试"""

    def test_ffmpeg_in_path(self, monkeypatch):
        """Scenario: ffmpeg 在 PATH 中"""
        import shutil
        monkeypatch.setattr(shutil, "which", lambda x: "/usr/bin/" + x)
        from rmbg_video import check_ffmpeg
        ffmpeg, ffprobe = check_ffmpeg(None)
        assert ffmpeg == "/usr/bin/ffmpeg"
        assert ffprobe == "/usr/bin/ffprobe"

    def test_ffmpeg_not_in_path(self, monkeypatch):
        """Scenario: ffmpeg 不在 PATH 中"""
        import shutil
        monkeypatch.setattr(shutil, "which", lambda x: None)
        from rmbg_video import check_ffmpeg
        with pytest.raises(SystemExit):
            check_ffmpeg(None)

    def test_custom_ffmpeg_path(self, monkeypatch):
        """Scenario: 自定义 ffmpeg 路径"""
        import shutil
        import os

        def mock_which(x):
            return x  # just return the path as-is
        monkeypatch.setattr(shutil, "which", mock_which)
        monkeypatch.setattr(os.path, "isfile", lambda x: True)  # Allow any file path
        from rmbg_video import check_ffmpeg
        ffmpeg, ffprobe = check_ffmpeg("/custom/ffmpeg")
        assert ffmpeg == "/custom/ffmpeg"
        assert ffprobe == "/custom/ffprobe"


# === Task 2.1: get_video_info() 和 new_session() ===
# specs: video-processing / 视频帧提取, rembg session 复用, GPU自动检测

class TestGetVideoInfo:
    """视频信息获取测试"""

    def test_standard_video_properties(self, monkeypatch):
        """Scenario: 获取标准视频属性"""
        ffprobe_output = json.dumps({
            "streams": [
                {"codec_type": "video", "width": 1920, "height": 1080,
                 "avg_frame_rate": "30/1"},
                {"codec_type": "audio", "codec_name": "aac"}
            ]
        })

        def mock_run(cmd, capture_output, text, **kwargs):
            result = subprocess.CompletedProcess([], 0, stdout=ffprobe_output, stderr="")
            return result
        monkeypatch.setattr(subprocess, "run", mock_run)
        from rmbg_video import get_video_info
        w, h, fps, has_audio = get_video_info("ffprobe", "test.mp4")
        assert w == 1920
        assert h == 1080
        assert fps == 30.0
        assert has_audio is True

    def test_non_integer_framerate(self, monkeypatch):
        """Scenario: 获取非标准帧率"""
        ffprobe_output = json.dumps({
            "streams": [
                {"codec_type": "video", "width": 1280, "height": 720,
                 "avg_frame_rate": "30000/1001"},
            ]
        })

        def mock_run(cmd, capture_output, text, **kwargs):
            return subprocess.CompletedProcess([], 0, stdout=ffprobe_output, stderr="")
        monkeypatch.setattr(subprocess, "run", mock_run)
        from rmbg_video import get_video_info
        w, h, fps, has_audio = get_video_info("ffprobe", "test.mp4")
        assert fps == pytest.approx(29.97, abs=0.1)

    def test_no_audio_stream(self, monkeypatch):
        """Scenario: 无音频轨道的视频"""
        ffprobe_output = json.dumps({
            "streams": [
                {"codec_type": "video", "width": 640, "height": 480,
                 "avg_frame_rate": "25/1"},
            ]
        })

        def mock_run(cmd, capture_output, text, **kwargs):
            return subprocess.CompletedProcess([], 0, stdout=ffprobe_output, stderr="")
        monkeypatch.setattr(subprocess, "run", mock_run)
        from rmbg_video import get_video_info
        w, h, fps, has_audio = get_video_info("ffprobe", "test.mp4")
        assert has_audio is False

    def test_r_frame_rate_fallback(self, monkeypatch):
        """Scenario: 无 avg_frame_rate 时使用 r_frame_rate 回退"""
        ffprobe_output = json.dumps({
            "streams": [
                {"codec_type": "video", "width": 1920, "height": 1080,
                 "r_frame_rate": "24/1"},
            ]
        })

        def mock_run(cmd, capture_output, text, **kwargs):
            return subprocess.CompletedProcess([], 0, stdout=ffprobe_output, stderr="")
        monkeypatch.setattr(subprocess, "run", mock_run)
        from rmbg_video import get_video_info
        w, h, fps, has_audio = get_video_info("ffprobe", "test.mp4")
        assert fps == 24.0


class TestNewSession:
    """rembg session 创建测试"""

    def test_default_model(self, monkeypatch):
        """Scenario: 默认模型"""
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4"])
        from rmbg_video import parse_args, create_session
        args = parse_args()
        import rembg
        calls = []

        def mock_new_session(model, providers=None):
            calls.append(model)
            return object()
        monkeypatch.setattr(rembg, "new_session", mock_new_session)
        session = create_session(args)
        assert calls == ["birefnet-general"]

    def test_custom_model(self, monkeypatch):
        """Scenario: 显式指定模型名"""
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4", "--model", "birefnet-general"])
        from rmbg_video import parse_args, create_session
        args = parse_args()
        import rembg
        calls = []

        def mock_new_session(model, providers=None):
            calls.append(model)
            return object()
        monkeypatch.setattr(rembg, "new_session", mock_new_session)
        session = create_session(args)
        assert calls == ["birefnet-general"]

    def test_gpu_detection_available(self, monkeypatch):
        """Scenario: GPU 可用"""
        import onnxruntime as ort
        monkeypatch.setattr(ort, "get_available_providers",
                            lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"])
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4"])
        from rmbg_video import parse_args, create_session
        args = parse_args()
        import rembg
        calls = {}

        def mock_new_session(model, providers=None):
            calls["model"] = model
            calls["providers"] = providers
            return object()
        monkeypatch.setattr(rembg, "new_session", mock_new_session)
        session = create_session(args)
        assert calls["providers"] == ["CUDAExecutionProvider", "CPUExecutionProvider"]

    def test_gpu_detection_cpu_only(self, capsys, monkeypatch):
        """Scenario: 仅 CPU"""
        import onnxruntime as ort
        monkeypatch.setattr(ort, "get_available_providers",
                            lambda: ["CPUExecutionProvider"])
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4"])
        from rmbg_video import parse_args, create_session
        args = parse_args()
        import rembg

        def mock_new_session(model, providers=None):
            return object()
        monkeypatch.setattr(rembg, "new_session", mock_new_session)
        session = create_session(args)
        captured = capsys.readouterr()
        assert "未检测到 GPU" in captured.out or "未检测到 GPU" in captured.err

    def test_force_cpu(self, monkeypatch):
        """Scenario: 强制使用 CPU"""
        import onnxruntime as ort
        monkeypatch.setattr(ort, "get_available_providers",
                            lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"])
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4", "--no-gpu"])
        from rmbg_video import parse_args, create_session
        args = parse_args()
        import rembg
        calls = {}

        def mock_new_session(model, providers=None):
            calls["model"] = model
            calls["providers"] = providers
            return object()
        monkeypatch.setattr(rembg, "new_session", mock_new_session)
        session = create_session(args)
        assert calls["providers"] == ["CPUExecutionProvider"]


# === Task 3.1: process_video() 核心管道 ===
# specs: video-processing / 逐帧alpha matting抠图, 管道流式处理, 处理进度显示

class MockPopen:
    """模拟 ffmpeg 子进程管道"""

    def __init__(self, cmd, **kwargs):
        self.cmd = cmd
        self._stdin = kwargs.pop("stdin", None)
        self._stdout = kwargs.pop("stdout", None)
        self.returncode = 0

    @property
    def stdin(self):
        return self._stdin

    @property
    def stdout(self):
        return self._stdout

    def poll(self):
        return None  # still running

    def wait(self, timeout=None):
        return 0

    def terminate(self):
        pass

    def kill(self):
        pass


class FakePbar:
    """模拟 tqdm 进度条"""

    def __init__(self, **kwargs):
        pass

    def update(self, n=1):
        pass

    def close(self):
        pass


class BytesIOBuffer:
    """模拟可读写的管道缓冲区"""
    def __init__(self, data=b""):
        self._data = data
        self._pos = 0

    def read(self, size):
        chunk = self._data[self._pos:self._pos + size]
        self._pos += size
        return chunk

    def write(self, data):
        self._data += data

    def close(self):
        pass

    def tobytes(self):
        return self._data


FRAME_SIZE = 640 * 480 * 4  # RGBA frame


class TestProcessVideo:
    """process_video 核心函数测试"""

    @pytest.fixture
    def mock_setup(self, monkeypatch):
        """设置测试 fixtures"""
        import numpy as np

        # 创建测试帧数据 (RGBA)
        test_frame = np.zeros((480, 640, 4), dtype=np.uint8)
        test_frame[:, :, 3] = 255  # alpha channel opaque

        def mock_remove(data, session=None, alpha_matting=False,
                        alpha_matting_foreground_threshold=240,
                        alpha_matting_background_threshold=10,
                        alpha_matting_erode_size=10,
                        post_process_mask=False, **kwargs):
            # 返回处理后的 RGBA 帧 (模拟：背景透明)
            result = np.zeros((480, 640, 4), dtype=np.uint8)
            result[:, :, :3] = data[:, :, :3]  # 保留 RGB
            result[:, :, 3] = 128  # 半透明 alpha
            return result

        return {
            "test_frame": test_frame,
            "mock_remove": mock_remove,
        }

    def test_decoder_pipe_command(self, monkeypatch, mock_setup):
        """Scenario: 解码管道建立 — 命令包含 -f rawvideo -pix_fmt rgba pipe:stdout"""
        import numpy as np
        import rembg
        monkeypatch.setattr(rembg, "remove", mock_setup["mock_remove"])
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4"])

        decoder_cmds = []

        def capture_popen(cmd, **kwargs):
            decoder_cmds.append(cmd)
            if kwargs.get("stdin") == subprocess.PIPE:
                return MockPopen(cmd, stdin=BytesIOBuffer())
            buf = BytesIOBuffer(
                np.zeros(FRAME_SIZE, dtype=np.uint8).tobytes())
            return MockPopen(cmd, stdout=buf)

        monkeypatch.setattr(subprocess, "Popen", capture_popen)
        from rmbg_video import parse_args, process_video
        args = parse_args()
        session = object()
        process_video("ffmpeg", args.input, "/tmp/out.webm", session, 640, 480, 30.0,
                      alpha_matting=True, crf=10, speed="good", alpha=True)
        decoder_cmd = " ".join(decoder_cmds[0])
        assert "-f rawvideo" in decoder_cmd
        assert "pipe:stdout" in decoder_cmd or "pipe:1" in decoder_cmd

    def test_encoder_pipe_command(self, monkeypatch, mock_setup):
        """Scenario: 编码管道建立 — 命令包含 -c:v libvpx -pix_fmt yuva420p"""
        import numpy as np
        import rembg
        import tqdm
        monkeypatch.setattr(rembg, "remove", mock_setup["mock_remove"])
        monkeypatch.setattr(tqdm, "tqdm", lambda **kw: FakePbar())
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4"])

        encoder_cmds = []

        def capture_popen(cmd, **kwargs):
            if kwargs.get("stdin") == subprocess.PIPE:
                encoder_cmds.append(cmd)
                return MockPopen(cmd, stdin=BytesIOBuffer())
            buf = BytesIOBuffer(
                np.zeros(FRAME_SIZE, dtype=np.uint8).tobytes())
            return MockPopen(cmd, stdout=buf)

        monkeypatch.setattr(subprocess, "Popen", capture_popen)
        from rmbg_video import parse_args, process_video
        args = parse_args()
        session = object()
        process_video("ffmpeg", args.input, "/tmp/out.webm", session, 640, 480, 30.0,
                      alpha_matting=True, crf=10, speed="good", alpha=True)
        encoder_cmd = " ".join(encoder_cmds[0])
        assert "-c:v libvpx" in encoder_cmd
        assert "-pix_fmt yuva420p" in encoder_cmd
        assert "-auto-alt-ref 0" in encoder_cmd

    def test_no_alpha_output(self, monkeypatch, mock_setup):
        """Scenario: 不带透明通道的输出 (--no-alpha)"""
        import numpy as np
        import rembg
        import tqdm
        monkeypatch.setattr(rembg, "remove", mock_setup["mock_remove"])
        monkeypatch.setattr(tqdm, "tqdm", lambda **kw: FakePbar())
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4", "--no-alpha"])

        encoder_cmds = []

        def capture_popen(cmd, **kwargs):
            if kwargs.get("stdin") == subprocess.PIPE:
                encoder_cmds.append(cmd)
                return MockPopen(cmd, stdin=BytesIOBuffer())
            buf = BytesIOBuffer(
                np.zeros(FRAME_SIZE, dtype=np.uint8).tobytes())
            return MockPopen(cmd, stdout=buf)

        monkeypatch.setattr(subprocess, "Popen", capture_popen)
        from rmbg_video import parse_args, process_video
        args = parse_args()
        session = object()
        process_video("ffmpeg", args.input, "/tmp/out.webm", session, 640, 480, 30.0,
                      alpha_matting=True, crf=10, speed="good", alpha=False)
        encoder_cmd = " ".join(encoder_cmds[0])
        assert "yuv420p" in encoder_cmd
        assert "yuva420p" not in encoder_cmd

    def test_alpha_matting_defaults(self, monkeypatch, mock_setup):
        """Scenario: 默认 alpha matting 参数"""
        import numpy as np
        import rembg
        import tqdm
        remove_calls = []

        def track_remove(data, **kwargs):
            remove_calls.append(kwargs)
            result = np.zeros((480, 640, 4), dtype=np.uint8)
            result[:, :, :3] = data[:, :, :3]
            result[:, :, 3] = 128
            return result

        monkeypatch.setattr(rembg, "remove", track_remove)
        monkeypatch.setattr(tqdm, "tqdm", lambda **kw: FakePbar())
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4"])

        def capture_popen(cmd, **kwargs):
            if kwargs.get("stdin") == subprocess.PIPE:
                return MockPopen(cmd, stdin=BytesIOBuffer())
            buf = BytesIOBuffer(
                np.zeros(FRAME_SIZE, dtype=np.uint8).tobytes())
            return MockPopen(cmd, stdout=buf)

        monkeypatch.setattr(subprocess, "Popen", capture_popen)
        from rmbg_video import parse_args, process_video
        args = parse_args()
        session = object()
        process_video("ffmpeg", args.input, "/tmp/out.webm", session, 640, 480, 30.0,
                      alpha_matting=True, crf=10, speed="good", alpha=True)
        assert remove_calls
        call = remove_calls[0]
        assert call["alpha_matting"] is True
        assert call["alpha_matting_foreground_threshold"] == 240
        assert call["alpha_matting_background_threshold"] == 10
        assert call["alpha_matting_erode_size"] == 10

    def test_alpha_matting_disabled(self, monkeypatch, mock_setup):
        """Scenario: 禁用 alpha matting (--no-alpha-matting)"""
        import numpy as np
        import rembg
        import tqdm
        remove_calls = []

        def track_remove(data, **kwargs):
            remove_calls.append(kwargs)
            result = np.zeros((480, 640, 4), dtype=np.uint8)
            result[:, :, :3] = data[:, :, :3]
            result[:, :, 3] = 255
            return result

        monkeypatch.setattr(rembg, "remove", track_remove)
        monkeypatch.setattr(tqdm, "tqdm", lambda **kw: FakePbar())
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4", "--no-alpha-matting"])

        def capture_popen(cmd, **kwargs):
            if kwargs.get("stdin") == subprocess.PIPE:
                return MockPopen(cmd, stdin=BytesIOBuffer())
            buf = BytesIOBuffer(
                np.zeros(FRAME_SIZE, dtype=np.uint8).tobytes())
            return MockPopen(cmd, stdout=buf)

        monkeypatch.setattr(subprocess, "Popen", capture_popen)
        from rmbg_video import parse_args, process_video
        args = parse_args()
        session = object()
        process_video("ffmpeg", args.input, "/tmp/out.webm", session, 640, 480, 30.0,
                      alpha_matting=False, crf=10, speed="good", alpha=True)
        assert remove_calls
        assert remove_calls[0]["alpha_matting"] is False

    def test_post_process_mask(self, monkeypatch, mock_setup):
        """Scenario: 启用后处理遮罩 (--post-process-mask)"""
        import numpy as np
        import rembg
        import tqdm
        remove_calls = []

        def track_remove(data, **kwargs):
            remove_calls.append(kwargs)
            result = np.zeros((480, 640, 4), dtype=np.uint8)
            result[:, :, :3] = data[:, :, :3]
            result[:, :, 3] = 128
            return result

        monkeypatch.setattr(rembg, "remove", track_remove)
        monkeypatch.setattr(tqdm, "tqdm", lambda **kw: FakePbar())
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4", "--post-process-mask"])

        def capture_popen(cmd, **kwargs):
            if kwargs.get("stdin") == subprocess.PIPE:
                return MockPopen(cmd, stdin=BytesIOBuffer())
            buf = BytesIOBuffer(
                np.zeros(FRAME_SIZE, dtype=np.uint8).tobytes())
            return MockPopen(cmd, stdout=buf)

        monkeypatch.setattr(subprocess, "Popen", capture_popen)
        from rmbg_video import parse_args, process_video
        args = parse_args()
        session = object()
        process_video("ffmpeg", args.input, "/tmp/out.webm", session, 640, 480, 30.0,
                      alpha_matting=True, post_process_mask=True, crf=10, speed="good", alpha=True)
        assert remove_calls
        assert remove_calls[0]["post_process_mask"] is True

    def test_custom_alpha_params(self, monkeypatch, mock_setup):
        """Scenario: 自定义 alpha matting 参数"""
        import numpy as np
        import rembg
        import tqdm
        remove_calls = []

        def track_remove(data, **kwargs):
            remove_calls.append(kwargs)
            result = np.zeros((480, 640, 4), dtype=np.uint8)
            result[:, :, :3] = data[:, :, :3]
            result[:, :, 3] = 128
            return result

        monkeypatch.setattr(rembg, "remove", track_remove)
        monkeypatch.setattr(tqdm, "tqdm", lambda **kw: FakePbar())
        monkeypatch.setattr(sys, "argv", [
            "rmbg_video.py", "input.mp4",
            "--fg-threshold", "230", "--bg-threshold", "20", "--erode-size", "15"
        ])

        def capture_popen(cmd, **kwargs):
            if kwargs.get("stdin") == subprocess.PIPE:
                return MockPopen(cmd, stdin=BytesIOBuffer())
            buf = BytesIOBuffer(
                np.zeros(FRAME_SIZE, dtype=np.uint8).tobytes())
            return MockPopen(cmd, stdout=buf)

        monkeypatch.setattr(subprocess, "Popen", capture_popen)
        from rmbg_video import parse_args, process_video
        args = parse_args()
        session = object()
        process_video("ffmpeg", args.input, "/tmp/out.webm", session, 640, 480, 30.0,
                      alpha_matting=True, fg_threshold=230, bg_threshold=20, erode_size=15,
                      crf=10, speed="good", alpha=True)
        assert remove_calls
        assert remove_calls[0]["alpha_matting_foreground_threshold"] == 230
        assert remove_calls[0]["alpha_matting_background_threshold"] == 20
        assert remove_calls[0]["alpha_matting_erode_size"] == 15

    def test_crf_and_speed_params(self, monkeypatch, mock_setup):
        """Scenario: 可配置 CRF 质量和编码速度"""
        import numpy as np
        import rembg
        import tqdm
        monkeypatch.setattr(rembg, "remove", mock_setup["mock_remove"])
        monkeypatch.setattr(tqdm, "tqdm", lambda **kw: FakePbar())
        monkeypatch.setattr(sys, "argv", [
            "rmbg_video.py", "input.mp4", "--crf", "5", "--speed", "realtime"
        ])

        encoder_cmds = []

        def capture_popen(cmd, **kwargs):
            if kwargs.get("stdin") == subprocess.PIPE:
                encoder_cmds.append(cmd)
                return MockPopen(cmd, stdin=BytesIOBuffer())
            buf = BytesIOBuffer(
                np.zeros(FRAME_SIZE, dtype=np.uint8).tobytes())
            return MockPopen(cmd, stdout=buf)

        monkeypatch.setattr(subprocess, "Popen", capture_popen)
        from rmbg_video import parse_args, process_video
        args = parse_args()
        session = object()
        process_video("ffmpeg", args.input, "/tmp/out.webm", session, 640, 480, 30.0,
                      alpha_matting=True, crf=5, speed="realtime", alpha=True)
        encoder_cmd = " ".join(encoder_cmds[0])
        assert "-crf 5" in encoder_cmd
        assert "-deadline realtime" in encoder_cmd

    def test_progress_bar_created(self, monkeypatch, mock_setup):
        """Scenario: 进度条初始化（tqdm 被调用）"""
        import numpy as np
        import rembg
        import tqdm
        monkeypatch.setattr(rembg, "remove", mock_setup["mock_remove"])
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4"])

        tqdm_calls = []

        def fake_tqdm(**kwargs):
            tqdm_calls.append(kwargs)
            return FakePbar()

        monkeypatch.setattr(tqdm, "tqdm", fake_tqdm)

        def capture_popen(cmd, **kwargs):
            if kwargs.get("stdin") == subprocess.PIPE:
                return MockPopen(cmd, stdin=BytesIOBuffer())
            buf = BytesIOBuffer()
            return MockPopen(cmd, stdout=buf)

        monkeypatch.setattr(subprocess, "Popen", capture_popen)
        from rmbg_video import parse_args, process_video
        args = parse_args()
        session = object()
        process_video("ffmpeg", args.input, "/tmp/out.webm", session, 640, 480, 30.0,
                      alpha_matting=True, crf=10, speed="good", alpha=True)
        assert tqdm_calls
        assert tqdm_calls[0]["unit"] == "帧"

    def test_streaming_processing(self, monkeypatch, mock_setup):
        """Scenario: 流式帧处理 — 每帧从解码管道读取，处理后写入编码管道"""
        import numpy as np
        import rembg
        import tqdm

        # 准备 3 帧测试数据
        frame = np.zeros((480, 640, 4), dtype=np.uint8)
        frame[:, :, :3] = [100, 150, 200]
        frame_data = frame.tobytes()
        multi_frame_data = frame_data * 3  # 3 帧

        encoder_written = BytesIOBuffer()

        def capture_popen(cmd, **kwargs):
            if kwargs.get("stdin") == subprocess.PIPE:
                return MockPopen(cmd, stdin=encoder_written)
            buf = BytesIOBuffer(multi_frame_data)
            return MockPopen(cmd, stdout=buf)

        monkeypatch.setattr(subprocess, "Popen", capture_popen)

        remove_calls = []

        def track_remove(data, **kwargs):
            remove_calls.append(data)
            result = np.zeros((480, 640, 4), dtype=np.uint8)
            result[:, :, :3] = data[:, :, :3]
            result[:, :, 3] = 100
            return result

        monkeypatch.setattr(rembg, "remove", track_remove)
        monkeypatch.setattr(tqdm, "tqdm", lambda **kw: FakePbar())
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4"])

        from rmbg_video import parse_args, process_video
        args = parse_args()
        session = object()
        process_video("ffmpeg", args.input, "/tmp/out.webm", session, 640, 480, 30.0,
                      alpha_matting=True, crf=10, speed="good", alpha=True)
        assert len(remove_calls) == 3
        encoder_output = encoder_written.tobytes()
        assert len(encoder_output) == FRAME_SIZE * 3


# === Task 4.1: extract_audio() 和 mux_audio() ===
# specs: video-encoding / 音频提取, 音频混流

class TestExtractAudio:
    """音频提取测试"""

    def test_extract_audio_opus_command(self, monkeypatch):
        """Scenario: 有音频的视频 — 执行 libopus 提取"""
        import os
        popen_calls = []

        def capture_popen(cmd, **kwargs):
            popen_calls.append(cmd)
            return MockPopen(cmd)
        monkeypatch.setattr(subprocess, "Popen", capture_popen)
        monkeypatch.setattr(os.path, "isfile", lambda x: True)

        from rmbg_video import extract_audio
        result = extract_audio("ffmpeg", "input.mp4", "/tmp")
        assert result is not None
        extract_cmd = " ".join(popen_calls[0])
        assert "-vn" in extract_cmd
        assert "-c:a libopus" in extract_cmd
        assert "-b:a 96k" in extract_cmd

    def test_extract_audio_skip_when_no_audio(self, monkeypatch):
        """Scenario: 无音频的视频 — 跳过音频提取"""
        import os
        monkeypatch.setattr(os.path, "isfile", lambda x: False)

        class FailedPopen(MockPopen):
            def wait(self, timeout=None):
                return 1

        def capture_popen(cmd, **kwargs):
            return FailedPopen(cmd)

        monkeypatch.setattr(subprocess, "Popen", capture_popen)

        from rmbg_video import extract_audio
        result = extract_audio("ffmpeg", "input.mp4", "/tmp")
        assert result is None

    def test_extract_audio_no_audio_flag(self, monkeypatch):
        """Scenario: --no-audio 跳过音频处理（在 main 中处理）"""
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4", "--no-audio"])
        from rmbg_video import parse_args
        args = parse_args()
        assert args.no_audio is True


class TestMuxAudio:
    """音频混流测试"""

    def test_mux_audio_command(self, monkeypatch):
        """Scenario: 混流音视频"""
        run_calls = []

        def mock_run(cmd, check, **kwargs):
            run_calls.append(cmd)

        monkeypatch.setattr(subprocess, "run", mock_run)
        from rmbg_video import mux_audio
        mux_audio("ffmpeg", "/tmp/video.webm", "/tmp/audio.opus", "/tmp/output.webm")
        mux_cmd = " ".join(run_calls[0])
        assert "-c:v copy" in mux_cmd
        assert "-c:a copy" in mux_cmd
        assert "-map 0:v:0" in mux_cmd
        assert "-map 1:a:0" in mux_cmd
        assert "/tmp/output.webm" in mux_cmd

    def test_no_audio_copy_video(self, monkeypatch):
        """Scenario: 无音频时复制视频"""
        import shutil
        copy_calls = []

        def mock_copy2(src, dst):
            copy_calls.append((src, dst))

        monkeypatch.setattr(shutil, "copy2", mock_copy2)
        shutil.copy2("/tmp/video.webm", "/tmp/output.webm")
        assert copy_calls
        assert copy_calls[0] == ("/tmp/video.webm", "/tmp/output.webm")


# === Task 5.1: main() 编排与错误处理 ===
# specs: video-encoding / 临时文件管理

class TestMainOrchestration:
    """main() 编排测试"""

    def test_default_output_path(self, monkeypatch):
        """Scenario: 自动生成输出路径"""
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "/path/to/input.mp4"])
        from rmbg_video import parse_args
        args = parse_args()
        output = args.output or os.path.splitext(args.input)[0] + ".webm"
        assert output == "/path/to/input.webm"

    def test_keep_temp_flag(self, monkeypatch):
        """Scenario: --keep-temp 保留调试文件"""
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4", "--keep-temp"])
        from rmbg_video import parse_args
        args = parse_args()
        assert args.keep_temp is True

    def test_temp_dir_cleanup_normal(self, monkeypatch):
        """Scenario: 正常清理 — 临时目录被删除"""
        import shutil
        import tempfile

        rmtree_calls = []
        monkeypatch.setattr(shutil, "rmtree", lambda path, ignore_errors=False: rmtree_calls.append(path))

        temp_dir = tempfile.mkdtemp(prefix="test_rmbg_")
        # 正常模式清理
        keep_temp = False
        if not keep_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)
        assert len(rmtree_calls) == 1
        assert temp_dir in rmtree_calls[0]

    def test_temp_dir_keep(self, monkeypatch):
        """Scenario: --keep-temp 保留临时文件"""
        import shutil
        rmtree_calls = []

        monkeypatch.setattr(shutil, "rmtree", lambda path, ignore_errors=False: rmtree_calls.append(path))
        keep_temp = True
        if not keep_temp:
            shutil.rmtree("/tmp/test", ignore_errors=True)
        assert len(rmtree_calls) == 0

    def test_keyboard_interrupt_cleanup(self, monkeypatch):
        """Scenario: Ctrl+C 中断 → 终止子进程并清理"""
        terminate_calls = []

        class InterruptiblePopen(MockPopen):
            def terminate(self):
                terminate_calls.append("terminated")

        proc = InterruptiblePopen(["ffmpeg", "..."])
        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt:
            if proc.poll() is None:
                proc.terminate()
        assert len(terminate_calls) == 1


# === Task: 取消处理 ===
# specs: cancel-processing / cancel_event未设置时正常处理, cancel_event已设置时抛出异常,
#        CLI模式兼容

class TestProcessingCancelled:
    """ProcessingCancelled 异常类测试"""

    def test_exception_is_defined(self):
        """Scenario: ProcessingCancelled 异常类可导入且继承自 Exception"""
        from rmbg_video import ProcessingCancelled
        assert issubclass(ProcessingCancelled, Exception)

    def test_exception_can_be_raised_and_caught(self):
        """Scenario: ProcessingCancelled 可被抛出和捕获"""
        from rmbg_video import ProcessingCancelled
        with pytest.raises(ProcessingCancelled, match="测试取消"):
            raise ProcessingCancelled("测试取消")


class TestProcessVideoCancel:
    """process_video 取消行为测试"""

    def test_cancel_during_processing(self, monkeypatch):
        """Scenario: 处理期间设置 cancel_event → 抛出 ProcessingCancelled"""
        import numpy as np
        import rembg
        import tqdm
        import threading

        monkeypatch.setattr(rembg, "remove", lambda data, **kwargs: data)
        monkeypatch.setattr(tqdm, "tqdm", lambda **kw: FakePbar())
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4"])

        frame = np.zeros((480, 640, 4), dtype=np.uint8)
        frame_data = frame.tobytes() * 1000  # 足够多帧确保 timer 有时间触发

        def capture_popen(cmd, **kwargs):
            if kwargs.get("stdin") == subprocess.PIPE:
                return MockPopen(cmd, stdin=BytesIOBuffer())
            return MockPopen(cmd, stdout=BytesIOBuffer(frame_data))

        monkeypatch.setattr(subprocess, "Popen", capture_popen)

        from rmbg_video import parse_args, process_video, ProcessingCancelled
        args = parse_args()
        cancel_event = threading.Event()

        def delayed_cancel():
            cancel_event.set()

        timer = threading.Timer(0.001, delayed_cancel)
        timer.start()

        session = object()
        try:
            with pytest.raises(ProcessingCancelled):
                process_video("ffmpeg", args.input, "/tmp/out.webm", session,
                              640, 480, 30.0, cancel_event=cancel_event)
        finally:
            timer.cancel()

    def test_cancel_before_processing(self, monkeypatch):
        """Scenario: 处理前已设置 cancel_event → 立即抛出 ProcessingCancelled"""
        import numpy as np
        import rembg
        import tqdm
        import threading

        monkeypatch.setattr(rembg, "remove", lambda data, **kwargs: data)
        monkeypatch.setattr(tqdm, "tqdm", lambda **kw: FakePbar())
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4"])

        frame_data = np.zeros(FRAME_SIZE, dtype=np.uint8).tobytes()

        def capture_popen(cmd, **kwargs):
            if kwargs.get("stdin") == subprocess.PIPE:
                return MockPopen(cmd, stdin=BytesIOBuffer())
            return MockPopen(cmd, stdout=BytesIOBuffer(frame_data))

        monkeypatch.setattr(subprocess, "Popen", capture_popen)

        from rmbg_video import parse_args, process_video, ProcessingCancelled
        args = parse_args()
        cancel_event = threading.Event()
        cancel_event.set()

        session = object()
        with pytest.raises(ProcessingCancelled):
            process_video("ffmpeg", args.input, "/tmp/out.webm", session,
                          640, 480, 30.0, cancel_event=cancel_event)

    def test_no_cancel_event_passed(self, monkeypatch):
        """Scenario: 未传 cancel_event（CLI 模式）→ 正常完成不抛异常"""
        import numpy as np
        import rembg
        import tqdm

        monkeypatch.setattr(rembg, "remove", lambda data, **kwargs: data)
        monkeypatch.setattr(tqdm, "tqdm", lambda **kw: FakePbar())
        monkeypatch.setattr(sys, "argv", ["rmbg_video.py", "input.mp4"])

        frame_data = np.zeros(FRAME_SIZE, dtype=np.uint8).tobytes()

        def capture_popen(cmd, **kwargs):
            if kwargs.get("stdin") == subprocess.PIPE:
                return MockPopen(cmd, stdin=BytesIOBuffer())
            return MockPopen(cmd, stdout=BytesIOBuffer(frame_data))

        monkeypatch.setattr(subprocess, "Popen", capture_popen)

        from rmbg_video import parse_args, process_video
        args = parse_args()
        session = object()
        # 应无异常完成
        process_video("ffmpeg", args.input, "/tmp/out.webm", session,
                      640, 480, 30.0)
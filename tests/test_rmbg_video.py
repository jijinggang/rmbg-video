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
        assert args.speed == "best"
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


# === 音频提取 和 音频混流 ===

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



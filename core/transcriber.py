"""
Transcription Manager

Handles AI transcription using Faster Whisper.
This module has NO Blender dependencies.
"""

import os
import sys
import tempfile
import wave
import ctypes
import subprocess
from pathlib import Path
from typing import Iterator, List, Dict, Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class TranscriptionSegment:
    """Single transcription segment"""

    start: float  # Start time in seconds
    end: float  # End time in seconds
    text: str  # Transcribed text
    words: Optional[List[Dict]] = None  # Word-level timestamps if enabled


class TranscriptionManager:
    """Manages transcription using Faster Whisper"""

    def __init__(
        self,
        model_name: str = "base",
        device: str = "auto",
        compute_type: str = "default",
    ):
        """Initialize transcription manager

        Args:
            model_name: Model size (tiny, base, small, medium, large-v3)
            device: Device to use (auto, cpu, cuda)
            compute_type: Computation type (default, int8, float16, float32)
        """
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self._progress_callback = None
        self.last_error: str = ""

    def _prepare_cuda_runtime(self) -> None:
        """Best-effort CUDA runtime setup for pip/uv-installed NVIDIA libs."""
        if self.device != "cuda":
            return

        lib_dirs = []
        for base in sys.path:
            base_path = Path(base)
            for rel in (
                ("nvidia", "cuda_runtime", "lib"),
                ("nvidia", "cublas", "lib"),
                ("nvidia", "cudnn", "lib"),
                ("nvidia", "cufft", "lib"),
            ):
                candidate = base_path.joinpath(*rel)
                if candidate.is_dir():
                    lib_dirs.append(str(candidate))

        if lib_dirs:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            existing_parts = [p for p in existing.split(":") if p]
            merged = []
            for path in lib_dirs + existing_parts:
                if path not in merged:
                    merged.append(path)
            os.environ["LD_LIBRARY_PATH"] = ":".join(merged)

        # Preload commonly missing CUDA libs so ctranslate2/faster-whisper can resolve them.
        # Use absolute paths first because runtime LD_LIBRARY_PATH changes are not always honored.
        preload_order = (
            "libcudart.so.12",
            "libnvrtc.so.12",
            "libnvJitLink.so.12",
            "libcublasLt.so.12",
            "libcublas.so.12",
            "libcudnn.so.9",
            "libcufft.so.11",
        )

        def _try_load(lib_identifier: str) -> bool:
            try:
                ctypes.CDLL(lib_identifier, mode=ctypes.RTLD_GLOBAL)
                return True
            except OSError:
                return False

        for lib_name in preload_order:
            loaded = False

            for lib_dir in lib_dirs:
                candidate = os.path.join(lib_dir, lib_name)
                if os.path.exists(candidate) and _try_load(candidate):
                    loaded = True
                    break

            if loaded:
                continue

            # Fallback to loader lookup by library name.
            _try_load(lib_name)

    def load_model(self, cache_dir: Optional[str] = None) -> bool:
        """Load the Whisper model

        Args:
            cache_dir: Directory to cache downloaded models

        Returns:
            True if model loaded successfully
        """
        self.last_error = ""
        try:
            from faster_whisper import WhisperModel

            # Auto-detect device
            if self.device == "auto":
                import torch

                if torch.cuda.is_available():
                    self.device = "cuda"
                else:
                    self.device = "cpu"

            self._prepare_cuda_runtime()

            # Determine model path
            model_path_or_size = self.model_name
            download_root = cache_dir

            # PRE-CHECK: Validate model files exist before attempting to load
            if cache_dir:
                local_model_path = os.path.join(cache_dir, self.model_name)

                # Check if model directory exists
                if os.path.exists(local_model_path):
                    bin_path = os.path.join(local_model_path, "model.bin")
                    config_path = os.path.join(local_model_path, "config.json")

                    # Check existence AND size > 1KB/10B
                    has_bin = (
                        os.path.exists(bin_path) and os.path.getsize(bin_path) > 1024
                    )
                    has_config = (
                        os.path.exists(config_path)
                        and os.path.getsize(config_path) > 10
                    )

                    if has_bin and has_config:
                        # Model exists and looks complete - use local path
                        model_path_or_size = local_model_path
                        download_root = (
                            None  # Don't use download_root when path provided
                        )
                    elif os.path.exists(local_model_path):
                        # Directory exists but files incomplete
                        print(f"Error: Model '{self.model_name}' files are incomplete.")
                        print(
                            f"Expected: model.bin and config.json in {local_model_path}"
                        )
                        print(
                            f"Please re-download the model using the 'Download Model' button."
                        )
                        return False
                else:
                    # Model directory doesn't exist at all
                    print(f"Error: Model '{self.model_name}' not found.")
                    print(
                        f"Please download the model first using the 'Download Model' button in the addon panel."
                    )
                    return False

            # Auto-detect and adjust compute type for compatibility
            compute_type = self.compute_type
            if compute_type == "default":
                # Let faster-whisper handle default
                pass
            elif compute_type == "float16":
                # float16 only works efficiently on GPU
                if self.device == "cpu":
                    print(
                        f"Warning: float16 not supported on CPU, falling back to int8"
                    )
                    compute_type = "int8"
            # int8, float32 work on both CPU and GPU

            self.model = WhisperModel(
                model_path_or_size,
                device=self.device,
                compute_type=compute_type,
                download_root=download_root,
            )

            # Update the stored compute type to reflect what was actually used
            self.compute_type = compute_type
            return True

        except Exception as e:
            error_msg = str(e)
            self.last_error = error_msg

            # Provide user-friendly error messages
            if "float16" in error_msg and "not support" in error_msg:
                self.last_error = (
                    f"float16 compute type not supported on {self.device}. "
                    "Use int8 or float32."
                )
                print(f"Error: float16 compute type not supported on {self.device}")
                print(
                    f"Recommendation: Use 'int8' for CPU or 'float32' for broader compatibility"
                )
            elif "libcublas.so.12" in error_msg or "cannot be loaded" in error_msg:
                self.last_error = (
                    "CUDA runtime library missing/unloadable (libcublas.so.12). "
                    "Reinstall PyTorch from addon, ensure CUDA runtime deps are installed, "
                    "then restart Blender. If it persists, launch Blender from a shell with "
                    "LD_LIBRARY_PATH including site-packages/nvidia/*/lib."
                )
                print(
                    "Error: CUDA runtime library missing/unloadable (libcublas.so.12)"
                )
                print(
                    "Recommendation: Reinstall PyTorch and CUDA runtime deps from addon, then restart Blender."
                )
            elif (
                "No such file or directory" in error_msg
                or "does not appear to have a file named" in error_msg
            ):
                self.last_error = f"Model '{self.model_name}' files are missing. Download/re-download the model."
                print(f"Error: Model '{self.model_name}' not found.")
                print(f"Please download the model using the 'Download Model' button.")
            else:
                print(f"Error loading model: {e}")

            return False

    def set_progress_callback(self, callback: Callable[[float, str], None]):
        """Set callback for progress updates

        Args:
            callback: Function(progress: float, status: str) -> None
        """
        self._progress_callback = callback

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        translate: bool = False,
        beam_size: int = 5,
        word_timestamps: bool = False,
        vad_filter: bool = True,
        vad_parameters: Optional[Dict] = None,
    ) -> Iterator[TranscriptionSegment]:
        """Transcribe audio file

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en', 'auto' for auto-detect)
            translate: Translate to English
            word_timestamps: Include word-level timestamps
            vad_filter: Filter out non-speech
            vad_parameters: Dictionary of VAD parameters (threshold, min_speech_duration_ms, etc.)

        Yields:
            TranscriptionSegment objects
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Set up options
        options: Dict[str, Any] = {
            "word_timestamps": word_timestamps,
            "vad_filter": vad_filter,
        }

        if beam_size and beam_size > 0:
            options["beam_size"] = beam_size

        if vad_filter and vad_parameters:
            options["vad_parameters"] = vad_parameters

        if language and language != "auto":
            options["language"] = language

        if translate:
            options["task"] = "translate"

        # Transcribe
        segments, info = self.model.transcribe(audio_path, **options)

        # Report detection info
        if self._progress_callback:
            detected_lang = info.language if hasattr(info, "language") else "unknown"
            self._progress_callback(0.1, f"Detected language: {detected_lang}")

        # Process segments
        total_duration = self._get_audio_duration(audio_path)
        segment_count = 0

        for segment in segments:
            segment_count += 1

            # Create segment data
            seg_data = TranscriptionSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text.strip(),
                words=None,
            )

            # Add word timestamps if available
            if word_timestamps and hasattr(segment, "words"):
                seg_data.words = [
                    {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                    }
                    for word in segment.words
                ]

            # Report progress
            if self._progress_callback and total_duration > 0:
                progress = min(0.1 + (segment.end / total_duration) * 0.9, 1.0)
                self._progress_callback(
                    progress, f"Processing segment {segment_count}..."
                )

            yield seg_data

        # Complete
        if self._progress_callback:
            self._progress_callback(
                1.0, f"Transcription complete ({segment_count} segments)"
            )

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio file duration in seconds"""
        try:
            # Try using soundfile first (works with many formats)
            try:
                import soundfile as sf

                info = sf.info(audio_path)
                return info.duration
            except ImportError:
                pass

            # Fallback to wave (WAV only)
            with wave.open(audio_path, "rb") as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                return frames / float(rate)

        except Exception:
            return 0.0

    def get_audio_duration(self, audio_path: str) -> float:
        """Public wrapper for audio duration estimation."""
        return self._get_audio_duration(audio_path)

    @staticmethod
    def extract_audio(video_path: str, output_path: Optional[str] = None) -> str:
        """Extract audio from video file

        Args:
            video_path: Path to video file
            output_path: Output audio path (default: temp WAV file)

        Returns:
            Path to extracted audio file
        """
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)

        try:
            # Try ffmpeg first
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video_path,
                    "-vn",
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    output_path,
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {result.stderr}")

            return output_path

        except FileNotFoundError:
            # Fallback to pydub if available
            try:
                from pydub import AudioSegment

                audio = AudioSegment.from_file(video_path)
                audio.export(
                    output_path, format="wav", parameters=["-ar", "16000", "-ac", "1"]
                )
                return output_path
            except ImportError:
                raise RuntimeError(
                    "Neither ffmpeg nor pydub available for audio extraction"
                )

    @staticmethod
    def separate_vocals(audio_path: str) -> tuple[str, str]:
        """Run Demucs vocal separation and return (vocals_path, temp_output_dir)."""
        output_dir = tempfile.mkdtemp(prefix="subtitle_demucs_")
        model_name = "htdemucs_ft"

        cmd = [
            sys.executable,
            "-m",
            "demucs.separate",
            "--two-stems",
            "vocals",
            "-n",
            model_name,
            "-o",
            output_dir,
            audio_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if "No module named demucs" in stderr:
                raise RuntimeError(
                    "Vocal separation requires Demucs. Install 'demucs' first."
                )
            raise RuntimeError(f"Vocal separation failed: {stderr or 'unknown error'}")

        input_stem = Path(audio_path).stem
        expected = Path(output_dir) / model_name / input_stem / "vocals.wav"
        if expected.exists():
            return str(expected), output_dir

        fallback = list(Path(output_dir).glob("**/vocals.wav"))
        if fallback:
            return str(fallback[0]), output_dir

        raise RuntimeError("Vocal separation completed but vocals.wav was not found")

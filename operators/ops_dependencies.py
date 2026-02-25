"""
Dependency Management Operators

Handles checking and installing dependencies like faster-whisper, torch, etc.
"""

import bpy
import sys
import logging
from bpy.types import Operator
from ..core.dependency_manager import (
    DependencyManager,
    build_install_plan,
    build_install_step,
    execute_install_plan,
)
from ..config import __addon_name__
from ..hardening.error_boundary import execute_with_boundary


logger = logging.getLogger(__name__)


def _schedule_scene_update(scene_name, updater):
    def _apply():
        scene = bpy.data.scenes.get(scene_name)
        if not scene:
            return None
        props = scene.subtitle_editor
        updater(props)
        return None

    bpy.app.timers.register(_apply, first_interval=0.0)


class SUBTITLE_OT_check_dependencies(Operator):
    """Check if required dependencies are installed"""

    bl_idname = "subtitle.check_dependencies"
    bl_label = "Check Dependencies"
    bl_description = "Verify that all required dependencies are installed"
    bl_options = {"REGISTER", "INTERNAL"}

    def execute(self, context):
        props = context.scene.subtitle_editor

        # Debug: Print Python paths
        print("\n=== Subtitle Studio Dependency Check ===")
        print(f"Python executable: {sys.executable}")
        print(f"Python version: {sys.version}")
        print(f"sys.path contains {len(sys.path)} paths:")
        for i, p in enumerate(sys.path[:5]):  # Print first 5 paths
            print(f"  {i}: {p}")
        if len(sys.path) > 5:
            print(f"  ... and {len(sys.path) - 5} more paths")

        # Check each dependency
        deps_status = {
            "faster_whisper": False,
            "torch": False,
            "pysubs2": False,
            "onnxruntime": False,
        }

        # Check faster_whisper
        try:
            import faster_whisper

            deps_status["faster_whisper"] = True
            print("✓ faster_whisper found")
        except ImportError as e:
            print(f"✗ faster_whisper not found: {e}")

        # Check torch
        try:
            import torch

            deps_status["torch"] = True
            print("✓ torch found")
        except ImportError as e:
            print(f"✗ torch not found: {e}")

        # Check pysubs2
        try:
            import pysubs2

            deps_status["pysubs2"] = True
            print("✓ pysubs2 found")
        except ImportError as e:
            print(f"✗ pysubs2 not found: {e}")

        # Check onnxruntime
        try:
            import onnxruntime

            deps_status["onnxruntime"] = True
            print("✓ onnxruntime found")
        except ImportError as e:
            print(f"✗ onnxruntime not found: {e}")

        print("========================================\n")

        # Update properties
        props.deps_faster_whisper = deps_status["faster_whisper"]
        props.deps_torch = deps_status["torch"]
        props.deps_pysubs2 = deps_status["pysubs2"]
        props.deps_onnxruntime = deps_status["onnxruntime"]

        all_installed = all(deps_status.values())

        # Also check GPU status (CUDA, MPS, XPU)
        try:
            import torch

            gpu_detected = False

            if torch.cuda.is_available():
                gpu_detected = True
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                gpu_detected = True
            elif hasattr(torch, "xpu") and torch.xpu.is_available():
                gpu_detected = True

            props.gpu_detected = gpu_detected
        except (ImportError, AttributeError, RuntimeError):
            props.gpu_detected = False

        if all_installed:
            if props.gpu_detected:
                self.report({"INFO"}, "All dependencies installed - GPU ready")
            else:
                self.report(
                    {"WARNING"},
                    "All dependencies installed - No GPU detected (CPU only)",
                )
        else:
            missing = [k for k, v in deps_status.items() if not v]
            self.report({"WARNING"}, f"Missing dependencies: {', '.join(missing)}")

        return {"FINISHED"}


class SUBTITLE_OT_install_dependencies(Operator):
    """Install missing dependencies via consolidated modal operator"""

    bl_idname = "subtitle.install_dependencies"
    bl_label = "Install/Verify Dependencies"
    bl_description = (
        "Compatibility entrypoint that routes to the modal dependency installer"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        return bpy.ops.subtitle.download_dependencies("INVOKE_DEFAULT")


class SUBTITLE_OT_check_gpu(Operator):
    """Check if GPU is available for PyTorch"""

    bl_idname = "subtitle.check_gpu"
    bl_label = "Check GPU"
    bl_description = "Check if a compatible GPU is available"
    bl_options = {"REGISTER", "INTERNAL"}

    def execute(self, context):
        props = context.scene.subtitle_editor

        try:
            import torch

            gpu_info = []
            backend_detected = "cpu"  # Default to CPU

            # Check for NVIDIA CUDA
            if torch.cuda.is_available():
                props.gpu_detected = True
                gpu_name = torch.cuda.get_device_name(0)
                gpu_info.append(f"NVIDIA: {gpu_name}")
                backend_detected = "cuda"

                # Try to determine CUDA version
                try:
                    cuda_version = torch.version.cuda
                    if cuda_version:
                        # Map CUDA version to our naming
                        major_minor = cuda_version.split(".")[:2]
                        if major_minor == ["11", "8"]:
                            backend_detected = "cu118"
                        elif major_minor == ["12", "1"]:
                            backend_detected = "cu121"
                        elif major_minor == ["12", "4"]:
                            backend_detected = "cu124"
                except:
                    pass

            # Check for Apple Metal (MPS)
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                props.gpu_detected = True
                gpu_info.append("Apple Silicon (MPS)")
                backend_detected = "mps"

            # Check for Intel XPU
            elif hasattr(torch, "xpu") and torch.xpu.is_available():
                props.gpu_detected = True
                gpu_info.append("Intel Arc/XPU")
                backend_detected = "xpu"

            else:
                props.gpu_detected = False

            # Store detected backend
            props.pytorch_backend_detected = backend_detected

            # Check for mismatch with selected version
            selected_version = props.pytorch_version
            if selected_version != "cpu":
                # If user selected GPU but we detected CPU, it's a mismatch
                if backend_detected == "cpu":
                    props.pytorch_backend_mismatch = True
                    self.report(
                        {"WARNING"},
                        f"PyTorch backend mismatch: Selected {selected_version} but CPU-only detected. "
                        f"GPU may not be available or wrong PyTorch version installed.",
                    )
                # If user selected CUDA but we detected MPS/ROCm or different CUDA
                elif selected_version.startswith("cu") and backend_detected.startswith(
                    "cu"
                ):
                    # Both CUDA but different versions - warning but not mismatch
                    if selected_version != backend_detected:
                        self.report(
                            {"INFO"},
                            f"PyTorch working with {backend_detected} (selected {selected_version}). "
                            f"Reinstall to match exactly.",
                        )
                    props.pytorch_backend_mismatch = False
                elif selected_version != backend_detected:
                    props.pytorch_backend_mismatch = True
                    self.report(
                        {"WARNING"},
                        f"PyTorch backend mismatch: Selected {selected_version} but {backend_detected} detected.",
                    )
                else:
                    props.pytorch_backend_mismatch = False
            else:
                # User selected CPU
                if backend_detected == "cpu":
                    props.pytorch_backend_mismatch = False
                else:
                    # User selected CPU but GPU available - not a mismatch, just info
                    props.pytorch_backend_mismatch = False

            if gpu_info:
                self.report({"INFO"}, f"GPU(s) detected: {', '.join(gpu_info)}")
            else:
                self.report({"WARNING"}, "No GPU detected - will fallback to CPU")

        except ImportError:
            props.gpu_detected = False
            props.pytorch_backend_detected = ""
            props.pytorch_backend_mismatch = False
            self.report({"WARNING"}, "PyTorch not installed - cannot check GPU")
        except (AttributeError, RuntimeError, ValueError, OSError):
            props.gpu_detected = False
            self.report({"WARNING"}, "An unexpected error occurred while checking GPU.")

        return {"FINISHED"}


class SUBTITLE_OT_install_pytorch(Operator):
    """Install PyTorch with selected version"""

    bl_idname = "subtitle.install_pytorch"
    bl_label = "Install PyTorch"
    bl_description = "Install PyTorch with the selected version for your GPU"
    bl_options = {"REGISTER"}

    def execute(self, context):
        props = context.scene.subtitle_editor
        props.is_installing_pytorch = True
        props.pytorch_install_status = "Starting PyTorch installation..."

        addon_prefs = context.preferences.addons[__addon_name__].preferences
        use_uv = addon_prefs.use_uv
        pytorch_version = props.pytorch_version
        scene_name = context.scene.name if context.scene else ""

        # Run installation in background
        import threading

        thread = threading.Thread(
            target=self._install_thread, args=(scene_name, pytorch_version, use_uv)
        )
        thread.daemon = True
        thread.start()

        return {"FINISHED"}

    def _install_thread(self, scene_name, pytorch_version, use_uv):
        """Install PyTorch in background thread"""
        try:
            # Base PyTorch packages
            packages = ["torch", "torchaudio"]
            cuda_runtime_packages = [
                "nvidia-cuda-runtime-cu12",
                "nvidia-cublas-cu12",
                "nvidia-cudnn-cu12",
            ]

            # Determine installation method based on selection
            index_url = None
            use_mps = False

            if pytorch_version == "cpu":
                index_url = "https://download.pytorch.org/whl/cpu"
            elif pytorch_version == "cu118":
                index_url = "https://download.pytorch.org/whl/cu118"
            elif pytorch_version == "cu121":
                index_url = "https://download.pytorch.org/whl/cu121"
            elif pytorch_version == "cu124":
                index_url = "https://download.pytorch.org/whl/cu124"
            elif pytorch_version == "rocm57":
                index_url = "https://download.pytorch.org/whl/rocm5.7"
            elif pytorch_version == "mps":
                use_mps = True
                # MPS is included in standard PyTorch on macOS, no special index needed
            # For "auto", don't specify index_url - let pip choose

            # Install PyTorch
            _schedule_scene_update(
                scene_name,
                lambda props: setattr(
                    props,
                    "pytorch_install_status",
                    f"Installing PyTorch ({pytorch_version})...",
                ),
            )

            extra_args = ["--index-url", index_url] if index_url else []

            plan = build_install_plan(
                [
                    build_install_step(
                        name=f"pytorch-{pytorch_version}",
                        packages=packages,
                        constraint="numpy<2.0",
                        extra_args=extra_args,
                        use_uv=use_uv,
                    )
                ]
            )

            logger.info("Running install step: %s", plan.steps[0].name)
            _schedule_scene_update(
                scene_name,
                lambda props: setattr(
                    props,
                    "pytorch_install_status",
                    "Installing... Check System Console (Window > Toggle System Console) for progress...",
                ),
            )

            boundary = execute_with_boundary(
                "subtitle.pytorch.install",
                lambda: execute_install_plan(plan),
                logger,
                context={"version": pytorch_version, "use_uv": use_uv},
                fallback_message="PyTorch installation failed.",
            )

            if not boundary.ok:
                _schedule_scene_update(
                    scene_name,
                    lambda props: setattr(
                        props,
                        "pytorch_install_status",
                        f"Error: {boundary.user_message}",
                    ),
                )
                _schedule_scene_update(
                    scene_name,
                    lambda props: setattr(props, "is_installing_pytorch", False),
                )
                return

            result = boundary.value
            if result is None:
                _schedule_scene_update(
                    scene_name,
                    lambda props: setattr(
                        props,
                        "pytorch_install_status",
                        "Installation cancelled.",
                    ),
                )
                _schedule_scene_update(
                    scene_name,
                    lambda props: setattr(props, "is_installing_pytorch", False),
                )
                return

            if result.returncode != 0:
                _schedule_scene_update(
                    scene_name,
                    lambda props: setattr(
                        props,
                        "pytorch_install_status",
                        "Error: Installation failed. Check System Console for details.",
                    ),
                )
                _schedule_scene_update(
                    scene_name,
                    lambda props: setattr(props, "is_installing_pytorch", False),
                )
                return

            _schedule_scene_update(
                scene_name,
                lambda props: setattr(
                    props, "pytorch_install_status", "PyTorch installed successfully!"
                ),
            )

            # Install CUDA runtime libraries required by faster-whisper/ctranslate2.
            # This prevents runtime failures like missing libcublas.so.12.
            if pytorch_version in {"cu118", "cu121", "cu124"}:
                _schedule_scene_update(
                    scene_name,
                    lambda props: setattr(
                        props,
                        "pytorch_install_status",
                        "Installing CUDA runtime libraries for transcription...",
                    ),
                )

                runtime_plan = build_install_plan(
                    [
                        build_install_step(
                            name="cuda-runtime",
                            packages=cuda_runtime_packages,
                            use_uv=use_uv,
                        )
                    ]
                )

                logger.info("Running install step: %s", runtime_plan.steps[0].name)
                runtime_boundary = execute_with_boundary(
                    "subtitle.pytorch.cuda_runtime",
                    lambda: execute_install_plan(runtime_plan),
                    logger,
                    context={"version": pytorch_version, "use_uv": use_uv},
                    fallback_message="CUDA runtime library installation failed.",
                )

                if not runtime_boundary.ok:
                    _schedule_scene_update(
                        scene_name,
                        lambda props: setattr(
                            props,
                            "pytorch_install_status",
                            f"Error: {runtime_boundary.user_message}",
                        ),
                    )
                    return

                runtime_result = runtime_boundary.value
                if runtime_result is None:
                    _schedule_scene_update(
                        scene_name,
                        lambda props: setattr(
                            props,
                            "pytorch_install_status",
                            "CUDA runtime installation cancelled.",
                        ),
                    )
                    return

                if runtime_result.returncode != 0:
                    _schedule_scene_update(
                        scene_name,
                        lambda props: setattr(
                            props,
                            "pytorch_install_status",
                            "Error: CUDA runtime library install failed. Check System Console.",
                        ),
                    )
                    return

                _schedule_scene_update(
                    scene_name,
                    lambda props: setattr(
                        props,
                        "pytorch_install_status",
                        "PyTorch + CUDA runtime libraries installed successfully!",
                    ),
                )

            # Re-check dependencies to update torch status
            bpy.app.timers.register(
                lambda: bpy.ops.subtitle.check_dependencies(), first_interval=0.5
            )

            # Also check GPU status
            bpy.app.timers.register(
                lambda: bpy.ops.subtitle.check_gpu(), first_interval=1.0
            )

        except (RuntimeError, OSError, ValueError, AttributeError, TypeError) as e:
            _schedule_scene_update(
                scene_name,
                lambda props: setattr(
                    props, "pytorch_install_status", f"Error: {str(e)}"
                ),
            )
        finally:
            _schedule_scene_update(
                scene_name, lambda props: setattr(props, "is_installing_pytorch", False)
            )


classes = [
    SUBTITLE_OT_check_dependencies,
    SUBTITLE_OT_install_dependencies,
    SUBTITLE_OT_check_gpu,
    SUBTITLE_OT_install_pytorch,
]

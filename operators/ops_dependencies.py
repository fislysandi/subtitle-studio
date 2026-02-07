"""
Dependency Management Operators

Handles checking and installing dependencies like faster-whisper, torch, etc.
"""

import bpy
import subprocess
import sys
from bpy.types import Operator
from bpy.props import EnumProperty, BoolProperty


class SUBTITLE_OT_check_dependencies(Operator):
    """Check if required dependencies are installed"""

    bl_idname = "subtitle.check_dependencies"
    bl_label = "Check Dependencies"
    bl_description = "Verify that all required dependencies are installed"
    bl_options = {"REGISTER", "INTERNAL"}

    def execute(self, context):
        props = context.scene.subtitle_editor

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
        except ImportError:
            pass

        # Check torch
        try:
            import torch

            deps_status["torch"] = True
        except ImportError:
            pass

        # Check pysubs2
        try:
            import pysubs2

            deps_status["pysubs2"] = True
        except ImportError:
            pass

        # Check onnxruntime
        try:
            import onnxruntime

            deps_status["onnxruntime"] = True
        except ImportError:
            pass

        # Update properties
        props.deps_faster_whisper = deps_status["faster_whisper"]
        props.deps_torch = deps_status["torch"]
        props.deps_pysubs2 = deps_status["pysubs2"]
        props.deps_onnxruntime = deps_status["onnxruntime"]

        all_installed = all(deps_status.values())

        if all_installed:
            self.report({"INFO"}, "All dependencies are installed")
        else:
            missing = [k for k, v in deps_status.items() if not v]
            self.report({"WARNING"}, f"Missing dependencies: {', '.join(missing)}")

        return {"FINISHED"}


class SUBTITLE_OT_install_dependencies(Operator):
    """Install missing dependencies"""

    bl_idname = "subtitle.install_dependencies"
    bl_label = "Install/Verify Dependencies"
    bl_description = "Install missing dependencies. Future: Will allow PyTorch version selection for GPU compatibility"
    bl_options = {"REGISTER"}

    # Future: Add PyTorch version selection
    pytorch_version: EnumProperty(
        name="PyTorch Version",
        description="PyTorch version to install (for GPU compatibility)",
        items=[
            (
                "auto",
                "Auto (Recommended)",
                "Let pip choose the best version for your system",
            ),
            ("cpu", "CPU Only", "CPU-only version (no GPU support)"),
            ("cu118", "CUDA 11.8", "For older NVIDIA GPUs"),
            ("cu121", "CUDA 12.1", "For newer NVIDIA GPUs"),
            ("cu124", "CUDA 12.4", "For latest NVIDIA GPUs"),
            ("rocm", "ROCm (AMD)", "For AMD GPUs (Linux only)"),
        ],
        default="auto",
    )

    def execute(self, context):
        props = context.scene.subtitle_editor
        props.is_installing_deps = True
        props.deps_install_status = "Starting installation..."

        # Run installation in background
        import threading

        thread = threading.Thread(target=self._install_thread, args=(context,))
        thread.daemon = True
        thread.start()

        return {"FINISHED"}

    def _install_thread(self, context):
        """Install dependencies in background thread"""
        props = context.scene.subtitle_editor

        try:
            # Get Python executable
            python_exe = sys.executable

            # Base packages (always needed) - versions from pyproject.toml
            packages = [
                "faster-whisper",  # Latest version from UV
                "pysubs2>=1.8.0",
                "onnxruntime>=1.24.1",
            ]

            # PyTorch installation based on selection
            if self.pytorch_version == "auto":
                # Let pip resolve - will install with CUDA if available
                packages.append("torch")
                packages.append("torchaudio")
            elif self.pytorch_version == "cpu":
                packages.extend(
                    [
                        "torch",
                        "torchaudio",
                        "--index-url",
                        "https://download.pytorch.org/whl/cpu",
                    ]
                )
            elif self.pytorch_version.startswith("cu"):
                packages.extend(
                    [
                        f"torch",
                        f"torchaudio",
                        "--index-url",
                        f"https://download.pytorch.org/whl/{self.pytorch_version}",
                    ]
                )
            elif self.pytorch_version == "rocm":
                packages.extend(
                    [
                        "torch",
                        "torchaudio",
                        "--index-url",
                        "https://download.pytorch.org/whl/rocm5.7",
                    ]
                )

            # Install packages
            for i, package in enumerate(packages):
                if package.startswith("--"):
                    continue

                props.deps_install_status = f"Installing {package}..."

                cmd = [python_exe, "-m", "pip", "install", "-q", package]

                # Add index-url for PyTorch if specified
                if "torch" in package and self.pytorch_version != "auto":
                    if self.pytorch_version == "cpu":
                        cmd.extend(
                            ["--index-url", "https://download.pytorch.org/whl/cpu"]
                        )
                    elif self.pytorch_version.startswith("cu"):
                        cmd.extend(
                            [
                                "--index-url",
                                f"https://download.pytorch.org/whl/{self.pytorch_version}",
                            ]
                        )
                    elif self.pytorch_version == "rocm":
                        cmd.extend(
                            ["--index-url", "https://download.pytorch.org/whl/rocm5.7"]
                        )

                result = subprocess.run(
                    cmd, capture_output=True, text=True, check=False
                )

                if result.returncode != 0:
                    props.deps_install_status = (
                        f"Error installing {package}: {result.stderr[:200]}"
                    )
                    props.is_installing_deps = False
                    return

            props.deps_install_status = "Installation complete!"

            # Re-check dependencies
            bpy.app.timers.register(
                lambda: bpy.ops.subtitle.check_dependencies(), first_interval=0.5
            )

        except Exception as e:
            props.deps_install_status = f"Error: {str(e)}"
        finally:
            props.is_installing_deps = False

    def invoke(self, context, event):
        # For now, skip the dialog and install directly
        # Future: Show dialog for PyTorch version selection
        return self.execute(context)


classes = [
    SUBTITLE_OT_check_dependencies,
    SUBTITLE_OT_install_dependencies,
]

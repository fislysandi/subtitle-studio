"""
Dependency Management Operators

Handles checking and installing dependencies like faster-whisper, torch, etc.
"""

import bpy
import subprocess
import sys
from bpy.types import Operator
from ..core.dependency_manager import DependencyManager
from ..config import __addon_name__


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
        except Exception:
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
        except Exception:
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
    """Install missing dependencies"""

    bl_idname = "subtitle.install_dependencies"
    bl_label = "Install/Verify Dependencies"
    bl_description = "Install all dependencies (faster-whisper, pysubs2, onnxruntime). Use 'Install PyTorch' button below for GPU support"
    bl_options = {"REGISTER"}

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
        """Install dependencies in background thread (excluding PyTorch)"""
        props = context.scene.subtitle_editor

        try:
            # Base packages (always needed)
            # IMPORTANT: numpy<2.0 is required for compatibility with Blender's bundled modules
            packages = [
                "faster-whisper",
                "pysubs2>=1.8.0",
                "onnxruntime>=1.24.1",
            ]

            # Retrieve use_uv from Addon Preferences
            addon_prefs = context.preferences.addons[__addon_name__].preferences

            # Install all packages in a single command using UV dependency manager
            props.deps_install_status = "Bootstrapping UV & resolving dependencies..."

            # This handles uv bootstrap automatically if needed
            # We pass numpy<2.0 as constraint
            cmd = DependencyManager.get_install_command(
                packages, constraint="numpy<2.0", use_uv=addon_prefs.use_uv
            )

            print(f"Running command: {' '.join(cmd)}")
            props.deps_install_status = "Installing dependencies... Check System Console (Window > Toggle System Console) for details."

            # Run command (output goes to system console)
            result = subprocess.run(cmd, check=False)

            if result.returncode != 0:
                props.deps_install_status = (
                    "Error: Installation failed. Check System Console for details."
                )
                props.is_installing_deps = False
                return

            props.deps_install_status = (
                "Dependencies installed! Install PyTorch below for GPU support."
            )

            # Re-check dependencies
            bpy.app.timers.register(
                lambda: bpy.ops.subtitle.check_dependencies(), first_interval=0.5
            )

        except Exception as e:
            props.deps_install_status = f"Error: {str(e)}"
        finally:
            props.is_installing_deps = False


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

            # Check for NVIDIA CUDA
            if torch.cuda.is_available():
                props.gpu_detected = True
                gpu_name = torch.cuda.get_device_name(0)
                gpu_info.append(f"NVIDIA: {gpu_name}")

            # Check for Apple Metal (MPS)
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                props.gpu_detected = True
                gpu_info.append("Apple Silicon (MPS)")

            # Check for Intel XPU
            if hasattr(torch, "xpu") and torch.xpu.is_available():
                props.gpu_detected = True
                gpu_info.append("Intel Arc/XPU")

            if gpu_info:
                self.report({"INFO"}, f"GPU(s) detected: {', '.join(gpu_info)}")
            else:
                props.gpu_detected = False
                self.report({"WARNING"}, "No GPU detected - will fallback to CPU")

        except ImportError:
            props.gpu_detected = False
            self.report({"WARNING"}, "PyTorch not installed - cannot check GPU")
        except Exception:
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

        # Run installation in background
        import threading

        thread = threading.Thread(target=self._install_thread, args=(context,))
        thread.daemon = True
        thread.start()

        return {"FINISHED"}

    def _install_thread(self, context):
        """Install PyTorch in background thread"""
        props = context.scene.subtitle_editor
        pytorch_version = props.pytorch_version

        try:
            # Base PyTorch packages
            packages = ["torch", "torchaudio"]

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
            props.pytorch_install_status = f"Installing PyTorch ({pytorch_version})..."

            # Prepare extra args for index-url if needed
            extra_args = []
            if index_url:
                extra_args.extend(["--index-url", index_url])

            # Retrieve use_uv from Addon Preferences
            addon_prefs = context.preferences.addons[__addon_name__].preferences

            # IMPORTANT: numpy<2.0 is required for compatibility with aud module
            # Use DependencyManager to get uv/pip command
            cmd = DependencyManager.get_install_command(
                packages,
                constraint="numpy<2.0",
                extra_args=extra_args,
                use_uv=addon_prefs.use_uv,
            )

            print(f"Running command: {' '.join(cmd)}")
            props.pytorch_install_status = "Installing... Check System Console (Window > Toggle System Console) for progress..."

            # Run command (output goes to system console)
            result = subprocess.run(cmd, check=False)

            if result.returncode != 0:
                props.pytorch_install_status = (
                    "Error: Installation failed. Check System Console for details."
                )
                props.is_installing_pytorch = False
                return

            props.pytorch_install_status = "PyTorch installed successfully!"

            # Re-check dependencies to update torch status
            bpy.app.timers.register(
                lambda: bpy.ops.subtitle.check_dependencies(), first_interval=0.5
            )

            # Also check GPU status
            bpy.app.timers.register(
                lambda: bpy.ops.subtitle.check_gpu(), first_interval=1.0
            )

        except Exception as e:
            props.pytorch_install_status = f"Error: {str(e)}"
        finally:
            props.is_installing_pytorch = False


classes = [
    SUBTITLE_OT_check_dependencies,
    SUBTITLE_OT_install_dependencies,
    SUBTITLE_OT_check_gpu,
    SUBTITLE_OT_install_pytorch,
]

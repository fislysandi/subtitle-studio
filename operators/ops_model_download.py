"""
Simple Model Download - Subprocess Approach

No UI, no modal operators, just terminal output.
Uses subprocess to avoid GIL issues completely.
"""

import bpy
import subprocess
import sys
import os
from bpy.types import Operator
from ..utils import file_utils


class SUBTITLE_OT_download_model(Operator):
    """Download model in subprocess - terminal output only"""

    bl_idname = "subtitle.download_model"
    bl_label = "Download Model"
    bl_description = "Download Whisper model (output in terminal)"
    bl_options = {"REGISTER"}

    def execute(self, context):
        props = context.scene.subtitle_editor
        model_name = props.model

        # Get cache directory
        cache_dir = file_utils.get_addon_models_dir()

        # Get optional HF token
        preferences = context.preferences.addons.get("subtitle_editor")
        hf_token = None
        if preferences and hasattr(preferences, "preferences"):
            hf_token = preferences.preferences.hf_token or None

        print(f"\n{'=' * 60}")
        print(f"[Subtitle Editor] Starting download: {model_name}")
        print(f"[Subtitle Editor] Cache directory: {cache_dir}")
        print(
            f"[Subtitle Editor] HF Token: {'Set' if hf_token else 'Not set (anonymous)'}"
        )
        print(f"{'=' * 60}\n")

        # Create download script to run in subprocess
        script_content = f'''
import sys
sys.path.insert(0, "{os.path.dirname(__file__)}/../..")

from huggingface_hub import snapshot_download
import os

model_name = "{model_name}"
cache_dir = "{cache_dir}"
token = {repr(hf_token)}

repo_map = {{
    "tiny": "Systran/faster-whisper-tiny",
    "tiny.en": "Systran/faster-whisper-tiny.en", 
    "base": "Systran/faster-whisper-base",
    "base.en": "Systran/faster-whisper-base.en",
    "small": "Systran/faster-whisper-small",
    "small.en": "Systran/faster-whisper-small.en",
    "medium": "Systran/faster-whisper-medium",
    "medium.en": "Systran/faster-whisper-medium.en",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2", 
    "large-v3": "Systran/faster-whisper-large-v3",
    "large": "Systran/faster-whisper-large-v3",
    "distil-small.en": "Systran/faster-distil-whisper-small.en",
    "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
    "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
    "distil-large-v3.5": "distil-whisper/distil-large-v3.5-ct2",
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
}}

repo_id = repo_map.get(model_name, f"Systran/faster-whisper-{{model_name}}")

print(f"[Download] Starting download of {{model_name}} from {{repo_id}}")
print(f"[Download] Cache: {{cache_dir}}")
print(f"[Download] Token: {{'Yes' if token else 'No (anonymous)'}}")
print()

try:
    snapshot_download(
        repo_id=repo_id,
        cache_dir=cache_dir,
        token=token,
        local_files_only=False,
        resume_download=True,
    )
    print(f"\\n[Download] ✓ {{model_name}} download complete!")
    sys.exit(0)
except Exception as e:
    print(f"\\n[Download] ✗ Error: {{e}}")
    sys.exit(1)
'''

        # Write temporary script
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script_content)
            script_path = f.name

        try:
            # Run in subprocess
            # Using Popen to stream output in real-time
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            # Stream output to terminal
            for line in process.stdout:
                print(line, end="")

            # Wait for completion
            return_code = process.wait()

            if return_code == 0:
                print(f"\n{'=' * 60}")
                print(f"[Subtitle Editor] ✓ {model_name} ready!")
                print(f"{'=' * 60}\n")
                self.report({"INFO"}, f"Model {model_name} downloaded successfully!")
            else:
                print(f"\n{'=' * 60}")
                print(f"[Subtitle Editor] ✗ Download failed")
                print(f"{'=' * 60}\n")
                self.report({"ERROR"}, f"Failed to download {model_name}")

        finally:
            # Clean up temp script
            try:
                os.unlink(script_path)
            except:
                pass

        return {"FINISHED"}


classes = [SUBTITLE_OT_download_model]

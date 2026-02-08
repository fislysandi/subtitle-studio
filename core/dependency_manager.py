import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path


class DependencyManager:
    @staticmethod
    def get_uv_path():
        """
        Find uv executable.
        Checks:
        1. PATH (fastest)
        2. Typical installation locations
        """
        # Check PATH first
        uv_in_path = shutil.which("uv")
        if uv_in_path:
            return uv_in_path

        # Locations to check
        candidates = []

        # Relative to current python executable
        python_dir = Path(sys.executable).parent
        home = Path.home()

        if platform.system() == "Windows":
            # Windows locations
            candidates.append(python_dir / "uv.exe")
            candidates.append(python_dir / "Scripts" / "uv.exe")

            # User AppData
            appdata = os.environ.get("APPDATA")
            if appdata:
                candidates.append(Path(appdata) / "Python" / "Scripts" / "uv.exe")
        else:
            # Linux/Mac locations
            candidates.append(python_dir / "uv")
            candidates.append(python_dir / "bin" / "uv")
            candidates.append(home / ".local" / "bin" / "uv")

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return None

    @staticmethod
    def ensure_uv():
        """
        Ensure uv is installed.
        Returns path to uv executable or None if failed.
        """
        uv_path = DependencyManager.get_uv_path()
        if uv_path:
            return uv_path

        print("[Subtitle Studio] Bootstrapping uv...")
        try:
            # Install uv using standard pip
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "uv"],
                check=True,
                capture_output=False,
            )
            return DependencyManager.get_uv_path()
        except subprocess.CalledProcessError:
            try:
                # Fallback to --user
                print("[Subtitle Studio] Standard install failed, trying --user...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--user", "uv"],
                    check=True,
                    capture_output=False,
                )
                return DependencyManager.get_uv_path()
            except subprocess.CalledProcessError as e:
                print(f"[Subtitle Studio] Failed to bootstrap uv: {e}")
                return None

    @staticmethod
    def get_install_command(packages, constraint=None, extra_args=None, use_uv=True):
        """
        Get command to install packages using uv (preferred) or pip (fallback).
        Returns list of strings [executable, args...]
        """
        uv_path = DependencyManager.ensure_uv() if use_uv else None
        cmd = []

        if uv_path:
            print(f"[Subtitle Studio] Using uv: {uv_path}")
            # uv pip install --python <python_path> <packages>
            cmd = [uv_path, "pip", "install", "--python", sys.executable]
        else:
            if not use_uv:
                print("[Subtitle Studio] UV disabled by user settings, using pip")
            else:
                print("[Subtitle Studio] uv not found, falling back to pip")
            cmd = [sys.executable, "-m", "pip", "install"]

        # Add constraint first if provided
        if constraint:
            cmd.append(constraint)

        # Add packages
        cmd.extend(packages)

        # Add extra args (e.g. index-url)
        if extra_args:
            cmd.extend(extra_args)

        return cmd

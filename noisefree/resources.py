"""Paths that work both from source and inside a PyInstaller bundle."""
import os
import sys

APP_NAME = "NoiseFree"
APP_ID = "com.noisefree.app"
VERSION = "1.0.1"


def is_frozen():
    return hasattr(sys, "_MEIPASS")


def resource(*parts):
    base = sys._MEIPASS if is_frozen() else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def launch_command():
    """Command line that starts this app, used for launch-at-login."""
    if is_frozen():
        exe = sys.executable
        # Inside a macOS .app, launch the bundle rather than the inner binary.
        marker = ".app/Contents/MacOS/"
        if marker in exe:
            return ["open", "-a", exe.split(marker)[0] + ".app", "--args", "--minimized"]
        return [exe, "--minimized"]
    return [sys.executable, resource("main.py"), "--minimized"]

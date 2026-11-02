"""Build a self-contained NoiseFree app for the current OS.

    python build.py

Output in dist/:  NoiseFree.exe (Windows) · NoiseFree.app (macOS) · NoiseFree (Linux)
Everything the app needs (Python, Qt, ONNX Runtime, PortAudio, the models and,
on macOS, the BlackHole driver package) is bundled inside.
"""
import glob
import os
import plistlib
import shutil
import subprocess
import sys
import urllib.request

from PySide6.QtWidgets import QApplication

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from noisefree.denoiser import ensure_models  # noqa: E402
from noisefree.devices import BLACKHOLE_URL  # noqa: E402
from noisefree.resources import APP_ID, APP_NAME, VERSION  # noqa: E402
from noisefree.ui import icons  # noqa: E402

SEP = os.pathsep  # PyInstaller's src<sep>dest separator


def make_icon():
    _ = QApplication.instance() or QApplication([])
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    png = os.path.join(ROOT, "assets", "icon.png")
    icons.app_pixmap(1024).save(png)
    if sys.platform == "win32":
        from PIL import Image
        ico = os.path.join(ROOT, "assets", "icon.ico")
        Image.open(png).save(ico, sizes=[(s, s) for s in (16, 20, 24, 32, 48, 64, 128, 256)])
        return ico
    return png


def find_portaudio():
    for pattern in ("/usr/lib/x86_64-linux-gnu/libportaudio.so.2*", "/usr/lib/aarch64-linux-gnu/libportaudio.so.2*",
                    "/usr/lib64/libportaudio.so.2*", "/usr/lib/libportaudio.so.2*"):
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[0]
    sys.exit("libportaudio2 not found: sudo apt install libportaudio2")


def main():
    import PyInstaller.__main__

    ensure_models()
    args = [
        os.path.join(ROOT, "main.py"),
        "--name", APP_NAME, "--noconfirm", "--clean", "--windowed",
        "--icon", make_icon(),
        "--add-data", f"{os.path.join(ROOT, 'models')}{SEP}models",
        "--exclude-module", "tkinter",
        "--distpath", os.path.join(ROOT, "dist"),
        "--workpath", os.path.join(ROOT, "build"),
        "--specpath", os.path.join(ROOT, "build"),
    ]
    if sys.platform == "darwin":
        vendor = os.path.join(ROOT, "vendor")
        os.makedirs(vendor, exist_ok=True)
        pkg = os.path.join(vendor, "BlackHole2ch.pkg")
        if not os.path.exists(pkg):
            urllib.request.urlretrieve(BLACKHOLE_URL, pkg)
        args += ["--add-data", f"{vendor}{SEP}vendor", "--osx-bundle-identifier", APP_ID]
    else:
        args += ["--onefile"]
    if sys.platform.startswith("linux"):
        # devices.py loads the bundled copy by this exact name
        lib = os.path.join(ROOT, "build", "libportaudio.so.2")
        os.makedirs(os.path.dirname(lib), exist_ok=True)
        shutil.copy(find_portaudio(), lib)
        args += ["--add-binary", f"{lib}{SEP}."]

    PyInstaller.__main__.run(args)

    if sys.platform == "darwin":
        plist_path = os.path.join(ROOT, "dist", f"{APP_NAME}.app", "Contents", "Info.plist")
        with open(plist_path, "rb") as f:
            plist = plistlib.load(f)
        plist.update({
            "CFBundleShortVersionString": VERSION,
            "NSMicrophoneUsageDescription": "NoiseFree removes background noise from your microphone.",
            "LSUIElement": False,
            "NSHighResolutionCapable": True,
        })
        with open(plist_path, "wb") as f:
            plistlib.dump(plist, f)
        # editing Info.plist invalidates PyInstaller's ad-hoc signature
        subprocess.run(["codesign", "--force", "--deep", "-s", "-",
                        os.path.join(ROOT, "dist", f"{APP_NAME}.app")], check=True)


if __name__ == "__main__":
    main()

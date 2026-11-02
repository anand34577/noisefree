"""Audio devices, the per-OS virtual microphone, and launch-at-login.

The app plays clean audio into a virtual cable; its other end is a microphone
that Teams, Zoom, Discord etc. can select:

  Windows  VB-CABLE    play to "CABLE Input"    -> mic "CABLE Output"
  macOS    BlackHole   play to "BlackHole 2ch"  -> mic "BlackHole 2ch"
  Linux    created here with pactl (PulseAudio / PipeWire) -> "NoiseFree Microphone"
"""
import ctypes
import ctypes.util
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass

from .resources import APP_ID, APP_NAME, VERSION, is_frozen, launch_command, resource

PLATFORM = "linux" if sys.platform.startswith("linux") else sys.platform

# Frozen Linux builds ship their own PortAudio next to the app.
if PLATFORM == "linux" and is_frozen():
    _bundled = resource("libportaudio.so.2")
    if os.path.exists(_bundled):
        _find = ctypes.util.find_library
        ctypes.util.find_library = lambda name: _bundled if name == "portaudio" else _find(name)

import sounddevice as sd  # noqa: E402

LINUX_SINK = "noisefree_sink"
LINUX_SOURCE = "noisefree_mic"

MIC_NAME = {"win32": "CABLE Output", "darwin": "BlackHole 2ch", "linux": "NoiseFree Microphone"}[PLATFORM] \
    if PLATFORM in ("win32", "darwin", "linux") else "virtual microphone"

VBCABLE_URL = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip"
BLACKHOLE_URL = "https://existential.audio/downloads/BlackHole2ch-0.6.1.pkg"

_CABLE_HINT = {"win32": "cable input", "darwin": "blackhole"}
_CABLE_MIC_HINT = {"win32": "cable output", "darwin": "blackhole"}


@dataclass(frozen=True)
class Device:
    key: str            # stable id saved in settings
    name: str           # shown to the user
    index: int          # PortAudio device index
    rate: float
    channels: int
    pulse: str = ""     # Linux: PulseAudio source/sink name routed through the "pulse" device


def rescan():
    """PortAudio only sees new or removed devices after re-initialising."""
    sd._terminate()
    sd._initialize()


def _hostapi():
    # WASAPI gives full device names and low latency on Windows.
    if PLATFORM == "win32":
        for i, h in enumerate(sd.query_hostapis()):
            if "WASAPI" in h["name"]:
                return i
    return sd.default.hostapi


def _portaudio_devices(kind):
    api = _hostapi()
    ch_key = "max_input_channels" if kind == "input" else "max_output_channels"
    out = []
    for i, d in enumerate(sd.query_devices()):
        if d["hostapi"] == api and d[ch_key] > 0:
            out.append(Device(d["name"], d["name"], i, d["default_samplerate"], d[ch_key]))
    default_idx = sd.query_hostapis(api)["default_input_device" if kind == "input" else "default_output_device"]
    return out, default_idx


def _pactl(*args):
    return subprocess.run(["pactl", *args], capture_output=True, text=True, check=True).stdout


def _pulse_index():
    for name in ("pulse", "pipewire", "default"):
        for i, d in enumerate(sd.query_devices()):
            if d["name"] == name:
                return i
    return None


def _pulse_list(kind):
    """[(name, description)] from `pactl list sources|sinks`."""
    items, name = [], None
    for line in _pactl("list", kind).splitlines():
        line = line.strip()
        if line.startswith("Name:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("Description:") and name:
            items.append((name, line.split(":", 1)[1].strip()))
            name = None
    return items


def _linux_devices(kind):
    idx = _pulse_index()
    pulse_kind = "sources" if kind == "input" else "sinks"
    info = _pactl("info")
    want = "Default Source:" if kind == "input" else "Default Sink:"
    default_name = next((ln.split(":", 1)[1].strip() for ln in info.splitlines() if ln.startswith(want)), "")
    devs, default = [], None
    for name, desc in _pulse_list(pulse_kind):
        if name.endswith(".monitor") or name in (LINUX_SINK, LINUX_SOURCE):
            continue
        dev = Device(name, desc, idx, 48000.0, 2, pulse=name)
        devs.append(dev)
        if name == default_name:
            default = dev
    return devs, default


def list_devices(kind):
    """(devices, default_device) for kind 'input' (mics) or 'output' (speakers/headphones).

    The virtual cable itself is hidden: picking it as a mic or monitor would loop audio.
    """
    if PLATFORM == "linux" and shutil.which("pactl") and _pulse_index() is not None:
        return _linux_devices(kind)
    devs, default = _portaudio_devices(kind)
    hint = (_CABLE_MIC_HINT if kind == "input" else _CABLE_HINT).get(PLATFORM)
    if hint:
        devs = [d for d in devs if hint not in d.name.lower()]
    default_dev = next((d for d in devs if d.index == default), devs[0] if devs else None)
    return devs, default_dev


def find_cable():
    """The virtual cable's playback side, or None if it isn't installed."""
    if PLATFORM == "linux":
        idx = _pulse_index()
        if idx is None or not shutil.which("pactl"):
            return None
        if LINUX_SINK not in _pactl("list", "short", "sinks"):
            return None
        return Device(LINUX_SINK, "NoiseFree Sink", idx, 48000.0, 2, pulse=LINUX_SINK)
    hint = _CABLE_HINT.get(PLATFORM)
    devs, _ = _portaudio_devices("output")
    return next((d for d in devs if hint and hint in d.name.lower()), None)


def open_stream(cls, dev, **kw):
    """Open an sd.InputStream/OutputStream on dev (routing to the right Pulse node on Linux)."""
    if dev.pulse:
        os.environ["PULSE_SOURCE" if cls is sd.InputStream else "PULSE_SINK"] = dev.pulse
    try:
        return cls(device=dev.index, samplerate=dev.rate, dtype="float32", latency="low", **kw)
    finally:
        os.environ.pop("PULSE_SOURCE", None)
        os.environ.pop("PULSE_SINK", None)


# ---------------------------------------------------------------- virtual cable

class LinuxVirtualMic:
    """Null sink + remapped source, created at start and removed on quit."""

    def __init__(self):
        self.modules = []

    def setup(self):
        if not shutil.which("pactl"):
            raise RuntimeError("PulseAudio or PipeWire (pactl) was not found.")
        if LINUX_SINK in _pactl("list", "short", "sinks"):
            return  # left over from an earlier run; reuse it
        self.modules.append(_pactl(
            "load-module", "module-null-sink", f"sink_name={LINUX_SINK}",
            "sink_properties=device.description=NoiseFree_Sink").strip())
        self.modules.append(_pactl(
            "load-module", "module-remap-source", f"master={LINUX_SINK}.monitor",
            f"source_name={LINUX_SOURCE}",
            "source_properties=device.description=NoiseFree_Microphone").strip())

    def teardown(self):
        for mod in reversed(self.modules):
            subprocess.run(["pactl", "unload-module", mod], capture_output=True)
        self.modules.clear()


def download(url, dest, progress=lambda frac: None):
    # existential.audio answers Python's default User-Agent with HTTP 406
    req = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/{VERSION}"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while chunk := r.read(64 * 1024):
            f.write(chunk)
            done += len(chunk)
            if total:
                progress(done / total)


def install_cable(progress=lambda frac: None):
    """Fetch and launch the official virtual cable installer. Blocks while downloading.

    VB-CABLE's licence forbids embedding it in another installer, so on Windows
    we download the unmodified package from vb-audio.com and open its own setup,
    where the user confirms the install. BlackHole (GPL-3.0) ships inside the
    macOS build, with a download fallback.
    """
    tmp = tempfile.mkdtemp(prefix="noisefree-")
    if PLATFORM == "win32":
        archive = os.path.join(tmp, "vbcable.zip")
        download(VBCABLE_URL, archive, progress)
        with zipfile.ZipFile(archive) as z:
            z.extractall(tmp)
        setup = "VBCABLE_Setup_x64.exe" if sys.maxsize > 2**32 else "VBCABLE_Setup.exe"
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", os.path.join(tmp, setup), None, tmp, 1)
        if rc <= 32:
            raise RuntimeError("The installer was cancelled or could not start.")
    elif PLATFORM == "darwin":
        pkg = resource("vendor", "BlackHole2ch.pkg")
        if not os.path.exists(pkg):
            pkg = os.path.join(tmp, "BlackHole2ch.pkg")
            download(BLACKHOLE_URL, pkg, progress)
        subprocess.run(["open", pkg], check=True)
    else:
        raise RuntimeError("On Linux the virtual microphone is created automatically.")


# ---------------------------------------------------------------- launch at login

def _quote(cmd):
    return " ".join(f'"{c}"' if " " in c else c for c in cmd)


def autostart_enabled():
    if PLATFORM == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
                winreg.QueryValueEx(k, APP_NAME)
                return True
        except OSError:
            return False
    return os.path.exists(_autostart_file())


def set_autostart(on):
    cmd = launch_command()
    if PLATFORM == "win32":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run",
                            0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, _quote(cmd))
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except OSError:
                    pass
        return
    path = _autostart_file()
    if not on:
        if os.path.exists(path):
            os.remove(path)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        if PLATFORM == "darwin":
            args = "".join(f"<string>{c}</string>" for c in cmd)
            f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                    f'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict>'
                    f'<key>Label</key><string>{APP_ID}</string><key>ProgramArguments</key><array>{args}</array>'
                    f'<key>RunAtLoad</key><true/></dict></plist>\n')
        else:
            f.write(f"[Desktop Entry]\nType=Application\nName={APP_NAME}\nExec={_quote(cmd)}\n"
                    "X-GNOME-Autostart-enabled=true\n")


def _autostart_file():
    if PLATFORM == "darwin":
        return os.path.expanduser(f"~/Library/LaunchAgents/{APP_ID}.plist")
    return os.path.expanduser("~/.config/autostart/noisefree.desktop")

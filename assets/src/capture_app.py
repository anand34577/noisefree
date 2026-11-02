"""Capture the real NoiseFree windows for the README images.

    python assets/src/capture_app.py

Renders the app at 2x with a fixed set of devices and meter levels, without
opening audio streams or touching your saved settings. Output goes to
assets/src/app/*.png, which the HTML layouts in this folder embed.
"""
import os
import sys
import tempfile

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_SCALE_FACTOR"] = "2"

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from PySide6.QtCore import QSettings, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from noisefree import devices  # noqa: E402
from noisefree.devices import Device  # noqa: E402
from noisefree.engine import Engine  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
MICS = [Device("mv7", "Microphone (Shure MV7)", 0, 48000, 1),
        Device("jabra", "Headset Microphone (Jabra Evolve2 65)", 1, 48000, 1),
        Device("array", "Microphone Array (Realtek(R) Audio)", 2, 48000, 2)]
OUTS = [Device("sony", "Headphones (Sony WH-1000XM5)", 3, 48000, 2),
        Device("spk", "Speakers (Realtek(R) Audio)", 4, 48000, 2)]
CABLE = Device("cable", "CABLE Input (VB-Audio Virtual Cable)", 5, 48000, 2)

state = {"cable": CABLE}
devices.list_devices = lambda kind: (MICS, MICS[0]) if kind == "input" else (OUTS, OUTS[0])
devices.find_cable = lambda: state["cable"]
devices.rescan = lambda: None
devices.autostart_enabled = lambda: True
devices.PLATFORM = "win32"
Engine.load_model = lambda self, p: (setattr(self, "denoiser", None), ("DmlExecutionProvider", False))[1]
Engine.start = lambda self, *a: setattr(self, "running", True)
Engine.set_monitor = lambda self, dev: None

app = QApplication(sys.argv)
app.setStyle("Fusion")

from noisefree.ui import window  # noqa: E402

ini = os.path.join(tempfile.mkdtemp(), "capture.ini")
window.QSettings = lambda *a: QSettings(ini, QSettings.IniFormat)
window.QSystemTrayIcon.isSystemTrayAvailable = staticmethod(lambda: False)
os.makedirs(OUT, exist_ok=True)

w = window.MainWindow()


def talk(level_in=0.11, level_out=0.07):
    """Settle the meters at a speaking level with background noise removed."""
    w.meter_timer.stop()
    for _ in range(40):
        w.meter_in.push(level_in)
        w.meter_out.push(level_out)
    w.meter_in._peak = min(1.0, w.meter_in._v + 0.06)
    w.meter_out._peak = min(1.0, w.meter_out._v + 0.05)
    w.power.set_level(w.meter_out._v)


def set_theme(mode):
    w.settings.setValue("theme", mode)
    i = w.theme_combo.findData(mode)
    w.theme_combo.setCurrentIndex(i)
    w.apply_theme()


def shot(name):
    app.processEvents()
    w._fit_height()
    app.processEvents()
    w.repaint()
    w.grab().save(os.path.join(OUT, name + ".png"))


def run():
    w.strength.setValue(85)
    w.monitor_toggle.set_checked_silent(True)
    w._refresh_state()
    for mode in ("dark", "light"):
        set_theme(mode)
        talk()
        shot(f"home-{mode}")
    w.show_settings()
    for mode in ("dark", "light"):
        set_theme(mode)
        shot(f"settings-{mode}")
    w.show_home()
    state["cable"] = None
    w.cable = None
    w.monitor_toggle.set_checked_silent(False)
    w._refresh_state()
    for mode in ("dark", "light"):
        set_theme(mode)
        talk(0.05, 0.004)
        shot(f"setup-{mode}")
    w.install_state, w.install_progress = "downloading", 0.64
    w._refresh_banner()
    set_theme("light")
    shot("install-light")
    w.engine.running = False
    app.quit()


w.show()
QTimer.singleShot(1500, run)
app.exec()
print("saved to", OUT)

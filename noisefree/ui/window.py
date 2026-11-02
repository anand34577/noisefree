import threading

from PySide6.QtCore import QObject, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QGuiApplication, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import devices
from ..denoiser import available_providers, friendly
from ..engine import Engine
from ..resources import APP_NAME, VERSION
from . import icons, theme
from .widgets import Banner, Combo, FocusVisible, LevelMeter, PowerButton, Row, Themed, Toggle

PLATFORM = devices.PLATFORM
CABLE_PRODUCT = {"win32": "VB-CABLE", "darwin": "BlackHole"}.get(PLATFORM)


class Bridge(QObject):
    """Carries results from worker threads back to the UI thread."""
    model_ready = Signal(str, bool)
    install_progress = Signal(float)
    install_done = Signal(str)


def section(text):
    lbl = QLabel(text.upper())
    lbl.setProperty("role", "section")
    return lbl


def divider():
    line = QFrame(objectName="Divider")
    line.setFrameShape(QFrame.NoFrame)
    return line


def field(label, control, hint=""):
    """Label stacked above a full-width control."""
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(6)
    lbl = QLabel(label)
    lbl.setBuddy(control)
    v.addWidget(lbl)
    v.addWidget(control)
    w.hint = QLabel(hint, wordWrap=True)
    w.hint.setProperty("role", "muted")
    w.hint.setVisible(bool(hint))
    v.addWidget(w.hint)
    return w


class MainWindow(QMainWindow):
    def __init__(self, start_hidden=False):
        super().__init__()
        self.settings = QSettings(APP_NAME, APP_NAME)
        self.engine = Engine()
        self.bridge = Bridge()
        self.bridge.model_ready.connect(self._on_model_ready)
        self.bridge.install_progress.connect(self._on_install_progress)
        self.bridge.install_done.connect(self._on_install_done)

        self.linux_mic = None
        self.linux_error = ""
        self.mics, self.outputs, self.cable = [], [], None
        self.model_loaded = False
        self.active_provider, self.fell_back = "", False
        self.start_error = ""
        self.install_state, self.install_progress, self.install_error = None, 0.0, ""
        self._quitting = False

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(icons.app_icon())
        self.setFixedWidth(400)

        self.stack = QStackedWidget(objectName="Root")
        self.setCentralWidget(self.stack)
        self.stack.addWidget(self._build_home())
        self.stack.addWidget(self._build_settings())
        self._build_tray()

        QShortcut(QKeySequence("Ctrl+,"), self, activated=self.show_settings)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.show_home)

        self.apply_theme()
        QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _: self.apply_theme())

        self.meter_timer = QTimer(self, interval=33, timeout=self._tick)
        self.meter_timer.start()
        self.retry_timer = QTimer(self, interval=2500, timeout=self._auto_retry)

        # Focus rings show only for keyboard focus (see FocusVisible).
        self._focus_filter = FocusVisible(self)
        QApplication.instance().installEventFilter(self._focus_filter)

        if not (start_hidden and self.tray.isVisible()):
            self.show()
        QTimer.singleShot(0, self._boot)

    # ------------------------------------------------------------------ layout

    def _build_home(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(0)

        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(icons.app_pixmap(56).scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        header.addWidget(logo)
        header.addSpacing(8)
        header.addWidget(QLabel(APP_NAME, objectName="AppName"))
        header.addStretch()
        self.settings_btn = QToolButton(cursor=Qt.PointingHandCursor, toolTip="Settings (Ctrl+,)")
        self.settings_btn.setAccessibleName("Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        header.addWidget(self.settings_btn)
        root.addLayout(header)
        root.addSpacing(12)

        self.power = PowerButton()
        self.power.setEnabled(False)
        self.power.toggled.connect(self._on_power)
        root.addWidget(self.power, 0, Qt.AlignHCenter)
        root.addSpacing(10)
        self.hero = QLabel("Starting…", objectName="Hero", alignment=Qt.AlignCenter)
        self.hero_sub = QLabel("Loading the noise-removal model", alignment=Qt.AlignCenter, wordWrap=True)
        self.hero_sub.setProperty("role", "secondary")
        root.addWidget(self.hero)
        root.addSpacing(4)
        root.addWidget(self.hero_sub)
        root.addSpacing(20)

        card = QFrame(objectName="Card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(16, 16, 16, 16)
        cv.setSpacing(14)

        self.mic_combo = Combo()
        self.mic_combo.setAccessibleName("Microphone")
        self.mic_combo.aboutToShow.connect(self._rescan_and_restart)
        self.mic_combo.activated.connect(self._on_mic_chosen)
        cv.addWidget(field("Microphone", self.mic_combo))

        meters = QVBoxLayout()
        meters.setSpacing(6)
        self.meter_in = LevelMeter("meter_raw", "Your microphone level")
        self.meter_out = LevelMeter("primary", "Level others hear")
        for text, meter in (("Your microphone", self.meter_in), ("What others hear", self.meter_out)):
            lbl = QLabel(text)
            lbl.setProperty("role", "muted")
            meters.addWidget(lbl)
            meters.addWidget(meter)
            meters.addSpacing(4)
        cv.addLayout(meters)
        cv.addWidget(divider())

        strength_head = QHBoxLayout()
        strength_lbl = QLabel("Strength")
        self.strength_val = QLabel()
        self.strength_val.setProperty("role", "value")
        strength_head.addWidget(strength_lbl)
        strength_head.addStretch()
        strength_head.addWidget(self.strength_val)
        self.strength = QSlider(Qt.Horizontal, minimum=0, maximum=100, singleStep=5, pageStep=10)
        self.strength.setAccessibleName("Noise removal strength")
        self.strength.setCursor(Qt.PointingHandCursor)
        strength_lbl.setBuddy(self.strength)
        self.strength.valueChanged.connect(self._on_strength)
        s = QVBoxLayout()
        s.setSpacing(4)
        s.addLayout(strength_head)
        s.addWidget(self.strength)
        cv.addLayout(s)

        self.monitor_toggle = Toggle("Hear yourself")
        self.monitor_toggle.toggled.connect(self._on_monitor)
        self.monitor_row = Row("Hear yourself", self.monitor_toggle, icon_name="headphones")
        cv.addWidget(self.monitor_row)
        root.addWidget(card)
        root.addSpacing(12)

        self.banner = Banner()
        root.addWidget(self.banner)
        root.addStretch()
        return page

    def _build_settings(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(12, 12, 12, 0)
        outer.setSpacing(0)
        header = QHBoxLayout()
        self.back_btn = QToolButton(cursor=Qt.PointingHandCursor, toolTip="Back (Esc)")
        self.back_btn.setAccessibleName("Back")
        self.back_btn.clicked.connect(self.show_home)
        header.addWidget(self.back_btn)
        header.addSpacing(4)
        header.addWidget(QLabel("Settings", objectName="PageTitle"))
        header.addStretch()
        outer.addLayout(header)

        scroll = QScrollArea(widgetResizable=True, frameShape=QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget(objectName="SettingsBody")
        v = QVBoxLayout(body)
        v.setContentsMargins(8, 12, 8, 20)
        v.setSpacing(10)
        scroll.setWidget(body)
        outer.addWidget(scroll)

        def card(*widgets):
            c = QFrame(objectName="Card")
            cl = QVBoxLayout(c)
            cl.setContentsMargins(16, 14, 16, 14)
            cl.setSpacing(14)
            for i, w in enumerate(widgets):
                if i:
                    cl.addWidget(divider())
                cl.addWidget(w)
            return c

        # Processing
        self.provider_combo = Combo()
        self.provider_combo.setAccessibleName("Run the AI model on")
        for p in available_providers():
            self.provider_combo.addItem("Automatic (recommended)" if p == "auto" else friendly(p), p)
        self.provider_combo.activated.connect(self._on_provider_chosen)
        self.provider_field = field("Run the AI model on", self.provider_combo, " ")
        v.addWidget(section("Processing"))
        v.addWidget(card(self.provider_field))
        v.addSpacing(8)

        # Hear yourself
        self.monitor_combo = Combo()
        self.monitor_combo.setAccessibleName("Listen through")
        self.monitor_combo.aboutToShow.connect(self._rescan_and_restart)
        self.monitor_combo.activated.connect(self._on_monitor_device)
        v.addWidget(section("Hear yourself"))
        v.addWidget(card(field("Listen through", self.monitor_combo,
                               "Use headphones so your speakers don't echo back into the mic.")))
        v.addSpacing(8)

        # App
        self.theme_combo = Combo()
        self.theme_combo.setAccessibleName("Appearance")
        for label, val in (("Match system", "system"), ("Light", "light"), ("Dark", "dark")):
            self.theme_combo.addItem(label, val)
        self.theme_combo.activated.connect(self._on_theme_chosen)
        self.autostart_toggle = Toggle("Open when I sign in")
        self.autostart_toggle.toggled.connect(self._on_autostart)
        self.tray_toggle = Toggle("Keep running when closed")
        self.tray_toggle.toggled.connect(lambda on: self.settings.setValue("close_to_tray", on))
        v.addWidget(section("App"))
        v.addWidget(card(
            field("Appearance", self.theme_combo),
            Row("Open when I sign in", self.autostart_toggle, "Starts quietly in the system tray."),
            Row("Keep running when closed", self.tray_toggle,
                "Closing the window keeps your clean mic working from the tray."),
        ))
        v.addSpacing(8)

        # Virtual mic
        self.cable_status = QLabel(wordWrap=True)
        self.cable_status.setProperty("role", "secondary")
        vm = QWidget()
        vml = QVBoxLayout(vm)
        vml.setContentsMargins(0, 0, 0, 0)
        vml.setSpacing(10)
        vml.addWidget(self.cable_status)
        if CABLE_PRODUCT:
            self.reinstall_btn = QPushButton(f"Install {CABLE_PRODUCT}", cursor=Qt.PointingHandCursor)
            self.reinstall_btn.clicked.connect(self.install_cable)
            vml.addWidget(self.reinstall_btn, 0, Qt.AlignLeft)
        v.addWidget(section("Virtual microphone"))
        v.addWidget(card(vm))
        v.addSpacing(8)

        # About
        credits = {"win32": 'VB-CABLE by VB-Audio (donationware, <a href="https://vb-audio.com/Cable/">vb-cable.com</a>)',
                   "darwin": 'BlackHole by Existential Audio (GPL-3.0)',
                   "linux": "PulseAudio / PipeWire"}.get(PLATFORM, "")
        about = QLabel(
            f"{APP_NAME} {VERSION}<br><br>"
            "Your audio is processed on this device and never leaves it.<br><br>"
            '<span>Noise removal: DTLN by N. Westhausen (MIT)<br>'
            f"Virtual cable: {credits}</span>", wordWrap=True, openExternalLinks=True)
        about.setProperty("role", "secondary")
        v.addWidget(section("About"))
        v.addWidget(card(about))
        v.addStretch()
        return page

    def _build_tray(self):
        self.tray = QSystemTrayIcon(icons.app_icon(), self)
        menu = QMenu()
        self.tray_power = QAction("Noise removal", menu, checkable=True)
        self.tray_power.toggled.connect(lambda on: self.power.setChecked(on))
        menu.addAction(self.tray_power)
        menu.addSeparator()
        menu.addAction("Open NoiseFree", self.show_window)
        menu.addAction("Quit", self.quit_app)
        self.tray_menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: self.show_window() if r in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    # ------------------------------------------------------------------ theme

    def apply_theme(self):
        mode = self.settings.value("theme", "system")
        t = theme.tokens(mode)
        self.tokens = t
        app = QApplication.instance()
        pal = app.palette()
        for role, key in ((QPalette.Window, "background"), (QPalette.Base, "surface"),
                          (QPalette.AlternateBase, "surface_subtle"), (QPalette.Text, "text_primary"),
                          (QPalette.WindowText, "text_primary"), (QPalette.ButtonText, "text_primary"),
                          (QPalette.Button, "surface"), (QPalette.Highlight, "primary_subtle"),
                          (QPalette.HighlightedText, "text_primary"), (QPalette.PlaceholderText, "text_muted"),
                          (QPalette.Link, "primary")):
            pal.setColor(role, QColor(t[key]))
        app.setPalette(pal)
        app.setStyleSheet(theme.stylesheet(t))
        for w in self.findChildren(QWidget):
            if isinstance(w, Themed):
                w.set_tokens(t)
        self.settings_btn.setIcon(icons.icon("sliders", t["text_secondary"], 20))
        self.back_btn.setIcon(icons.icon("back", t["text_secondary"], 20))
        theme.set_title_bar_dark(self, t is theme.DARK)

    # ------------------------------------------------------------------ boot & devices

    def _boot(self):
        s = self.settings
        self.strength.setValue(int(s.value("strength", 100)))
        self._on_strength(self.strength.value())
        self.power.set_checked_silent(s.value("enabled", True, type=bool))
        self.engine.enabled = self.power.isChecked()
        self.tray_power.setChecked(self.power.isChecked())
        self.monitor_toggle.set_checked_silent(False)  # never start with self-monitoring on
        self.tray_toggle.set_checked_silent(s.value("close_to_tray", True, type=bool))
        self.autostart_toggle.set_checked_silent(devices.autostart_enabled())
        idx = self.theme_combo.findData(s.value("theme", "system"))
        self.theme_combo.setCurrentIndex(max(0, idx))
        idx = self.provider_combo.findData(s.value("provider", "auto"))
        self.provider_combo.setCurrentIndex(max(0, idx))

        if PLATFORM == "linux":
            try:
                self.linux_mic = devices.LinuxVirtualMic()
                self.linux_mic.setup()
            except Exception as e:
                self.linux_mic, self.linux_error = None, str(e)
        self._scan()
        self._load_model(self.provider_combo.currentData())

    def _scan(self):
        self.mics, default_mic = devices.list_devices("input")
        self.outputs, default_out = devices.list_devices("output")
        self.cable = devices.find_cable()
        self._fill(self.mic_combo, self.mics, self.settings.value("mic", ""), default_mic,
                   "No microphone found")
        self._fill(self.monitor_combo, self.outputs, self.settings.value("monitor", ""), default_out,
                   "No speakers or headphones found")
        self._refresh_cable_ui()

    @staticmethod
    def _fill(combo, devs, saved_key, default, empty_text):
        combo.blockSignals(True)
        combo.clear()
        for d in devs:
            combo.addItem(d.name, d.key)
        if not devs:
            combo.addItem(empty_text, "")
        combo.setEnabled(bool(devs))
        idx = combo.findData(saved_key)
        if idx < 0 and default is not None:
            idx = combo.findData(default.key)
        combo.setCurrentIndex(max(0, idx))
        combo.blockSignals(False)

    def _selected(self, combo, devs):
        key = combo.currentData()
        return next((d for d in devs if d.key == key), None)

    def _rescan_and_restart(self):
        """Pick up newly plugged-in devices (PortAudio must be restarted to see them)."""
        was_running = self.engine.running
        self.engine.stop()
        devices.rescan()
        self._scan()
        if was_running or self.model_loaded:
            self._start_audio()

    # ------------------------------------------------------------------ model & audio

    def _load_model(self, provider):
        def work():
            p, fell_back = self.engine.load_model(provider)
            self.bridge.model_ready.emit(p, fell_back)
        threading.Thread(target=work, daemon=True).start()

    def _on_model_ready(self, provider, fell_back):
        first = not self.model_loaded
        self.model_loaded = True
        self.active_provider, self.fell_back = provider, fell_back
        hint = f"Running on {friendly(provider)}."
        if fell_back:
            hint = f"The selected processor wasn't available, so {APP_NAME} is using the CPU."
        self.provider_field.hint.setText(hint)
        self.provider_field.hint.setVisible(True)
        if first:
            self._start_audio()
            if self.power.isEnabled():
                self.power.setFocus(Qt.OtherFocusReason)

    def _start_audio(self):
        self.start_error = ""
        mic = self._selected(self.mic_combo, self.mics)
        if not mic:
            self.engine.stop()
            self._refresh_state()
            return
        monitor = self._selected(self.monitor_combo, self.outputs) if self.monitor_toggle.isChecked() else None
        try:
            self.engine.start(mic, self.cable, monitor)
            self.retry_timer.stop()
        except Exception as e:
            self.start_error = str(e) or e.__class__.__name__
        self._refresh_state()

    def _auto_retry(self):
        """While a device is missing, look for it again every few seconds."""
        if self.engine.running:
            self.retry_timer.stop()
            return
        devices.rescan()
        self._scan()
        if self._selected(self.mic_combo, self.mics):
            self._start_audio()

    def _tick(self):
        e = self.engine
        self.meter_in.push(e.level_in)
        self.meter_out.push(e.level_out)
        self.power.set_level(self.meter_out._v if e.enabled else 0.0)
        if e.error and e.running:
            e.stop()
            if e.error == "monitor":
                self.monitor_toggle.setChecked(False)
                e.error = None
                self._start_audio()
            else:
                self.retry_timer.start()
            self._refresh_state()

    # ------------------------------------------------------------------ state → UI

    def _refresh_state(self):
        e = self.engine
        ready = self.model_loaded and e.running
        self.power.setEnabled(ready)
        on = self.power.isChecked()
        self.strength.setEnabled(ready and on)

        if not self.model_loaded:
            hero, sub = "Starting…", "Loading the noise-removal model"
        elif not e.running:
            hero, sub = "Microphone unavailable", "Choose a microphone below to get started"
        elif on:
            hero, sub = "Noise removal is on", "Others hear your voice without background noise"
        else:
            hero, sub = "Noise removal is off", "Others hear your microphone as it is"
        self.hero.setText(hero)
        self.hero_sub.setText(sub)
        self.power.setToolTip(("Turn off" if on else "Turn on") + " noise removal (Space)")

        mon = self._selected(self.monitor_combo, self.outputs)
        self.monitor_row.hint.setText(
            f"Playing through {mon.name}. Use headphones to avoid echo." if self.monitor_toggle.isChecked() and mon
            else "Listen to the cleaned audio to check how you sound.")
        self.monitor_row.hint.setVisible(True)
        self.monitor_toggle.setEnabled(bool(self.outputs) and ready)

        tip = f"{APP_NAME}: noise removal {'on' if on else 'off'}"
        self.tray.setToolTip(tip)
        self.tray.setIcon(icons.app_icon(on and ready))
        self.tray_power.blockSignals(True)
        self.tray_power.setChecked(on)
        self.tray_power.blockSignals(False)
        self.tray_power.setEnabled(ready)
        self._refresh_banner()

    def _refresh_banner(self):
        b, e = self.banner, self.engine
        retry = ("Try again", self._rescan_and_restart)
        if e.error == "mic" or (self.model_loaded and not self.mics):
            b.show_state("error", "Microphone disconnected" if self.mics else "No microphone found",
                         "Plug one in. We'll pick it up automatically.", primary=retry)
        elif self.start_error:
            b.show_state("error", "Couldn't open the microphone", self.start_error, primary=retry)
        elif self.install_state == "downloading":
            b.show_state("info", f"Downloading {CABLE_PRODUCT}…", "This only takes a moment.",
                         progress=self.install_progress)
        elif self.install_error:
            b.show_state("error", "Installation didn't finish", self.install_error,
                         primary=("Try again", self.install_cable))
        elif not self.cable and PLATFORM == "linux":
            b.show_state("error", "Couldn't create the virtual microphone",
                         self.linux_error or "Make sure PulseAudio or PipeWire is running.", primary=retry)
        elif not self.cable and self.install_state == "launched":
            body = ("Click Install Driver in the VB-CABLE window, then restart your computer. "
                    "CABLE appears after the restart." if PLATFORM == "win32"
                    else "Finish the installer, then check again.")
            b.show_state("warning", "Almost there", body, primary=("Check again", self._recheck_cable))
        elif not self.cable:
            b.show_state("warning", "One more step: add the virtual microphone",
                         f"{CABLE_PRODUCT} is a free audio driver that lets Teams, Zoom and other apps "
                         "use your clean audio. You'll confirm the install in its own window.",
                         primary=(f"Install {CABLE_PRODUCT}", self.install_cable),
                         secondary=("Check again", self._recheck_cable))
        elif e.error == "cable":
            b.show_state("error", "The virtual microphone stopped", "", primary=retry)
        else:
            b.show_state("success", "Ready for your calls",
                         f"In Teams, Zoom or Discord, choose “{devices.MIC_NAME}” as your microphone.",
                         secondary=("Copy name", self._copy_mic_name))
        QTimer.singleShot(0, self._fit_height)

    def _fit_height(self):
        """Size the window to the home page exactly; banner and hint text change length."""
        lay = self.stack.widget(0).layout()
        h = lay.heightForWidth(self.width()) if lay.hasHeightForWidth() else lay.sizeHint().height()
        self.setFixedHeight(h)

    def _refresh_cable_ui(self):
        if self.cable:
            text = f"Installed. Meeting apps can use “{devices.MIC_NAME}” as their microphone."
        elif PLATFORM == "linux":
            text = "Created automatically while NoiseFree is open."
        else:
            text = f"Not installed yet. {CABLE_PRODUCT} is free and takes a minute."
        self.cable_status.setText(text)
        if CABLE_PRODUCT:
            self.reinstall_btn.setText(f"Reinstall {CABLE_PRODUCT}" if self.cable else f"Install {CABLE_PRODUCT}")

    # ------------------------------------------------------------------ actions

    def _on_power(self, on):
        self.engine.enabled = on
        self.settings.setValue("enabled", on)
        self._refresh_state()

    def _on_strength(self, v):
        self.engine.strength = v / 100
        self.strength_val.setText(f"{v}%")
        self.settings.setValue("strength", v)

    def _on_mic_chosen(self, _):
        self.settings.setValue("mic", self.mic_combo.currentData())
        self._start_audio()

    def _on_monitor(self, on):
        dev = self._selected(self.monitor_combo, self.outputs) if on else None
        try:
            self.engine.set_monitor(dev)
        except Exception:
            self.monitor_toggle.set_checked_silent(False)
        self._refresh_state()

    def _on_monitor_device(self, _):
        self.settings.setValue("monitor", self.monitor_combo.currentData())
        if self.monitor_toggle.isChecked():
            self._on_monitor(True)

    def _on_provider_chosen(self, _):
        p = self.provider_combo.currentData()
        self.settings.setValue("provider", p)
        self.provider_field.hint.setText("Switching…")
        self._load_model(p)

    def _on_theme_chosen(self, _):
        self.settings.setValue("theme", self.theme_combo.currentData())
        self.apply_theme()

    def _on_autostart(self, on):
        try:
            devices.set_autostart(on)
        except OSError:
            self.autostart_toggle.set_checked_silent(not on)

    def _copy_mic_name(self):
        QGuiApplication.clipboard().setText(devices.MIC_NAME)
        self.banner.secondary.setText("Copied")
        QTimer.singleShot(1500, lambda: self.banner.secondary.text() == "Copied" and
                          self.banner.secondary.setText("Copy name"))

    def install_cable(self):
        if self.install_state == "downloading":
            return
        self.install_state, self.install_progress, self.install_error = "downloading", 0.0, ""
        self.show_home()
        self._refresh_banner()

        def work():
            try:
                devices.install_cable(self.bridge.install_progress.emit)
                self.bridge.install_done.emit("")
            except Exception as e:
                self.bridge.install_done.emit(str(e) or "Something went wrong.")
        threading.Thread(target=work, daemon=True).start()

    def _on_install_progress(self, frac):
        self.install_progress = frac
        self._refresh_banner()

    def _on_install_done(self, err):
        self.install_state = None if err else "launched"
        self.install_error = err
        self._refresh_banner()

    def _recheck_cable(self):
        self._rescan_and_restart()
        if self.cable:
            self.install_state = None
        self._refresh_state()

    # ------------------------------------------------------------------ navigation & lifecycle

    def show_settings(self):
        self.stack.setCurrentIndex(1)
        self.back_btn.setFocus(Qt.OtherFocusReason)

    def show_home(self):
        self.stack.setCurrentIndex(0)

    def show_window(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def closeEvent(self, e):
        if not self._quitting and self.settings.value("close_to_tray", True, type=bool) and self.tray.isVisible():
            e.ignore()
            self.hide()
            if not self.settings.value("tray_hint_shown", False, type=bool):
                self.tray.showMessage(APP_NAME, "Still running in the background. Your clean mic keeps working. "
                                      "Quit from the tray icon.", icons.app_icon(), 4000)
                self.settings.setValue("tray_hint_shown", True)
            return
        self.quit_app()

    def quit_app(self):
        self._quitting = True
        self.engine.stop()
        if self.linux_mic:
            self.linux_mic.teardown()
        self.tray.hide()
        QApplication.instance().quit()

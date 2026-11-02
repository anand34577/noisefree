"""Custom-painted controls. Colours come from the active token set (see theme.py)."""
import math

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPointF, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme


def mix(a, b, t):
    a, b = QColor(a), QColor(b)
    return QColor(round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t))


def repolish(w):
    w.style().unpolish(w)
    w.style().polish(w)


KEYBOARD_REASONS = (Qt.TabFocusReason, Qt.BacktabFocusReason, Qt.ShortcutFocusReason)


class FocusVisible(QObject):
    """App-wide filter giving stylesheets a focus-visible state: [kbfocus="true"]."""

    def eventFilter(self, obj, e):
        t = e.type()
        if t in (QEvent.FocusIn, QEvent.FocusOut) and isinstance(obj, QWidget):
            kb = t == QEvent.FocusIn and e.reason() in KEYBOARD_REASONS
            if obj.property("kbfocus") != kb:
                obj.setProperty("kbfocus", kb)
                repolish(obj)
        return False


class Themed:
    """Mixin: widgets that paint themselves keep a reference to the token set."""
    tokens = theme.LIGHT

    def set_tokens(self, t):
        self.tokens = t
        self.update()


class _Animated(Themed):
    def _init_anim(self, start):
        self._t = start
        self._anim = QVariantAnimation(self, duration=theme.MOTION_MS, easingCurve=QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._tick)

    def _tick(self, v):
        self._t = v
        self.update()

    def _animate_to(self, end):
        if not theme.animations_enabled():
            self._tick(end)
            return
        self._anim.stop()
        self._anim.setStartValue(float(self._t))
        self._anim.setEndValue(float(end))
        self._anim.start()


class _KeyboardFocus:
    """Draw focus rings only for keyboard focus, like CSS :focus-visible."""
    _kb_focus = False

    def focusInEvent(self, e):
        self._kb_focus = e.reason() in KEYBOARD_REASONS
        super().focusInEvent(e)

    def focusOutEvent(self, e):
        self._kb_focus = False
        super().focusOutEvent(e)


class PowerButton(_KeyboardFocus, _Animated, QAbstractButton):
    """Large round on/off switch. A soft halo breathes with the outgoing voice level."""

    SIZE = 136
    RADIUS = 48

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName("Noise removal")
        self._init_anim(0.0)
        self._level = 0.0
        self.toggled.connect(lambda on: self._animate_to(1.0 if on else 0.0))

    def set_level(self, v):
        v = max(0.0, min(1.0, v))
        if abs(v - self._level) > 0.01:
            self._level = v
            self.update()

    def set_checked_silent(self, on):
        self.blockSignals(True)
        self.setChecked(on)
        self.blockSignals(False)
        self._tick(1.0 if on else 0.0)

    def hitButton(self, pos):
        c = self.SIZE / 2
        return math.hypot(pos.x() - c, pos.y() - c) <= self.RADIUS + 4

    def paintEvent(self, _):
        t, k = self._t, self.tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.SIZE / 2, self.SIZE / 2)
        r = float(self.RADIUS)
        if not self.isEnabled():
            p.setOpacity(0.45)

        if t > 0 and self.isEnabled():
            halo = QColor(k["primary"])
            halo.setAlphaF(0.16 * t)
            p.setPen(Qt.NoPen)
            p.setBrush(halo)
            halo_r = r + 6 + 12 * self._level * t
            p.drawEllipse(c, halo_r, halo_r)

        hover = self.underMouse() and self.isEnabled()
        off_fill = k["surface_hover"] if hover else k["surface"]
        on_fill = k["primary_hover"] if hover else k["primary"]
        fill = mix(off_fill, on_fill, t)
        if self.isDown():
            fill = fill.darker(108)
        p.setBrush(fill)
        border = mix(k["border_hover"], on_fill, t)
        p.setPen(QPen(border, 1.5))
        p.drawEllipse(c, r, r)

        ic = mix(k["text_secondary"], k["on_primary"], t).name()
        icons.paint(p, "power", ic, QRectF(c.x() - 20, c.y() - 20, 40, 40), stroke=2.2)

        if self.hasFocus() and self._kb_focus:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(k["focus"]), 2))
            p.drawEllipse(c, r + 5, r + 5)
        p.end()

    def enterEvent(self, e):
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)


class Toggle(_KeyboardFocus, _Animated, QAbstractButton):
    """iOS/Fluent-style switch, 40x22."""

    def __init__(self, accessible_name="", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self.setFixedSize(44, 26)
        self.setAccessibleName(accessible_name)
        self._init_anim(0.0)
        self.toggled.connect(lambda on: self._animate_to(1.0 if on else 0.0))

    def set_checked_silent(self, on):
        self.blockSignals(True)
        self.setChecked(on)
        self.blockSignals(False)
        self._tick(1.0 if on else 0.0)

    def paintEvent(self, _):
        t, k = self._t, self.tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.45)
        track = QRectF(2, 2, 40, 22)
        if self.hasFocus() and self._kb_focus:
            p.setPen(QPen(QColor(k["focus"]), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(track.adjusted(-1, -1, 1, 1), 12, 12)
        p.setPen(Qt.NoPen if t > 0.5 else QPen(QColor(k["border_hover"]), 1))
        p.setBrush(mix(k["surface_subtle"], k["primary"], t))
        p.drawRoundedRect(track, 11, 11)
        knob = 16
        x = track.left() + 3 + (track.width() - knob - 6) * t
        p.setPen(Qt.NoPen)
        p.setBrush(mix(k["text_secondary"], k["on_primary"], t))
        p.drawEllipse(QRectF(x, track.top() + 3, knob, knob))
        p.end()


class LevelMeter(Themed, QWidget):
    """Thin horizontal VU bar on a dB scale (-60..0 dBFS) with peak hold."""

    def __init__(self, color_key="primary", accessible_name="", parent=None):
        super().__init__(parent)
        self.color_key = color_key
        self.setFixedHeight(8)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAccessibleName(accessible_name)
        self._v = 0.0
        self._peak = 0.0

    def push(self, rms):
        db = 20 * math.log10(rms + 1e-9)
        target = max(0.0, min(1.0, (db + 60) / 60))
        # fast attack, slow release reads as "alive" without jitter
        self._v = target if target > self._v else self._v * 0.85 + target * 0.15
        self._peak = max(self._peak - 0.012, self._v)
        self.update()

    def paintEvent(self, _):
        k = self.tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(k["surface_subtle"]))
        p.drawRoundedRect(r, 4, 4)
        color = QColor(k[self.color_key])
        if self._v > 0.005:
            p.setBrush(color)
            p.drawRoundedRect(QRectF(0, 0, max(8.0, r.width() * self._v), r.height()), 4, 4)
        if self._peak > 0.02:
            x = r.width() * self._peak
            p.setBrush(color)
            p.drawRoundedRect(QRectF(min(x, r.width() - 3), 0, 3, r.height()), 1.5, 1.5)
        p.end()


class Combo(QComboBox):
    """QComboBox that announces when its popup is about to open (to rescan devices)."""
    aboutToShow = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.TabFocus)
        self.setCursor(Qt.PointingHandCursor)

    def showPopup(self):
        self.aboutToShow.emit()
        super().showPopup()


class IconLabel(Themed, QLabel):
    def __init__(self, name, color_key="text_secondary", size=18, parent=None):
        super().__init__(parent)
        self.name, self.color_key, self.size_ = name, color_key, size
        self.setFixedSize(size, size)

    def set_icon(self, name, color_key=None):
        self.name = name
        self.color_key = color_key or self.color_key
        self.set_tokens(self.tokens)

    def set_tokens(self, t):
        self.tokens = t
        self.setPixmap(icons.pixmap(self.name, t[self.color_key], self.size_))


class Banner(Themed, QFrame):
    """Status message with an icon, title, body and up to two actions."""

    KIND_ICON = {"success": ("check-circle", "success"), "warning": ("alert", "warning"),
                 "error": ("alert", "error"), "info": ("download", "primary")}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Banner")
        self.setAttribute(Qt.WA_StyledBackground)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 12, 12, 12)
        outer.setSpacing(12)
        self.icon = IconLabel("check-circle", "success", 20)
        outer.addWidget(self.icon, 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(2)
        self.title = QLabel(objectName="BannerTitle")
        self.body = QLabel(wordWrap=True)
        self.body.setProperty("role", "secondary")
        self.body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.progress = QProgressBar(textVisible=False, maximum=1000)
        self.progress.hide()
        col.addWidget(self.title)
        col.addWidget(self.body)
        col.addSpacing(2)
        col.addWidget(self.progress)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.setContentsMargins(0, 6, 0, 0)
        self.primary = QPushButton(cursor=Qt.PointingHandCursor)
        self.primary.setProperty("kind", "primary")
        self.secondary = QPushButton(cursor=Qt.PointingHandCursor)
        self.secondary.setProperty("kind", "ghost")
        actions.addWidget(self.primary)
        actions.addWidget(self.secondary)
        actions.addStretch()
        self.actions_row = QWidget()
        self.actions_row.setLayout(actions)
        col.addWidget(self.actions_row)
        outer.addLayout(col, 1)
        self._handlers = [None, None]
        self.primary.clicked.connect(lambda: self._handlers[0] and self._handlers[0]())
        self.secondary.clicked.connect(lambda: self._handlers[1] and self._handlers[1]())

    def show_state(self, kind, title, body, primary=None, secondary=None, progress=None):
        """primary/secondary: (label, callback) or None. progress: 0..1, or None to hide."""
        self.setProperty("kind", kind)
        repolish(self)
        name, color = self.KIND_ICON[kind]
        self.icon.set_icon(name, color)
        self.title.setText(title)
        self.body.setText(body)
        self.body.setVisible(bool(body))
        for btn, spec, i in ((self.primary, primary, 0), (self.secondary, secondary, 1)):
            btn.setVisible(spec is not None)
            if spec:
                btn.setText(spec[0])
                self._handlers[i] = spec[1]
        self.actions_row.setVisible(primary is not None or secondary is not None)
        self.progress.setVisible(progress is not None)
        if progress is not None:
            self.progress.setValue(int(progress * 1000))
        self.setAccessibleName(f"{title}. {body}")

    def set_tokens(self, t):
        self.tokens = t
        self.icon.set_tokens(t)


class Row(QWidget):
    """Label on the left, control on the right, optional hint underneath."""

    def __init__(self, label, control, hint="", icon_name=None, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        h = QHBoxLayout()
        h.setSpacing(10)
        if icon_name:
            self.icon = IconLabel(icon_name, "text_secondary", 18)
            h.addWidget(self.icon)
        self.label = QLabel(label)
        self.label.setBuddy(control)
        h.addWidget(self.label, 1)
        h.addWidget(control, 0, Qt.AlignRight | Qt.AlignVCenter)
        v.addLayout(h)
        self.hint = QLabel(hint, wordWrap=True)
        self.hint.setProperty("role", "muted")
        self.hint.setVisible(bool(hint))
        v.addWidget(self.hint)

    def sizeHint(self):
        return QSize(320, super().sizeHint().height())

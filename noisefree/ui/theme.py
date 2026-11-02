"""Design tokens and the Qt stylesheet built from them."""
import os
import sys
import tempfile

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from . import icons

LIGHT = {
    "background": "#F6F6F7",
    "surface": "#FFFFFF",
    "surface_subtle": "#EFEFF1",
    "surface_hover": "#E8E8EB",
    "surface_elevated": "#FFFFFF",
    "border": "#E1E1E5",
    "border_hover": "#C9C9D0",
    "text_primary": "#18181B",
    "text_secondary": "#52525B",
    "text_muted": "#6B6B74",
    "primary": "#0F766E",
    "primary_hover": "#115E59",
    "primary_subtle": "#E3F2F0",
    "on_primary": "#FFFFFF",
    "focus": "#0F766E",
    "success": "#15803D",
    "success_subtle": "#ECF7EF",
    "warning": "#B45309",
    "warning_subtle": "#FDF4E7",
    "error": "#B91C1C",
    "error_subtle": "#FCEDED",
    "meter_raw": "#A1A1AA",
}

DARK = {
    "background": "#111113",
    "surface": "#1A1A1D",
    "surface_subtle": "#26262A",
    "surface_hover": "#2C2C31",
    "surface_elevated": "#222226",
    "border": "#2E2E34",
    "border_hover": "#45454D",
    "text_primary": "#F4F4F5",
    "text_secondary": "#B4B4BC",
    "text_muted": "#8E8E98",
    "primary": "#2DD4BF",
    "primary_hover": "#5EEAD4",
    "primary_subtle": "#12302C",
    "on_primary": "#04201E",
    "focus": "#5EEAD4",
    "success": "#4ADE80",
    "success_subtle": "#132A1C",
    "warning": "#FBBF24",
    "warning_subtle": "#2E2410",
    "error": "#F87171",
    "error_subtle": "#331718",
    "meter_raw": "#6B6B74",
}

RADIUS = {"sm": 6, "md": 8, "lg": 14}
MOTION_MS = 160


def system_is_dark():
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def tokens(mode):
    """mode: 'system' | 'light' | 'dark'."""
    dark = system_is_dark() if mode == "system" else mode == "dark"
    return DARK if dark else LIGHT


def _chevron_file(color):
    path = os.path.join(tempfile.gettempdir(), f"noisefree-chevron-{color.strip('#')}@3x.png")
    if not os.path.exists(path):
        icons.pixmap("chevron", color, 16, dpr=3).save(path)
    return path.replace("\\", "/")


def stylesheet(t, framed=False):
    """framed: draw our own 1px window border (where the OS doesn't give a frameless window one)."""
    r = RADIUS
    chevron = _chevron_file(t["text_secondary"])
    frame = f"#Root {{ border: 1px solid {t['border_hover']}; }}" if framed else ""
    return f"""
* {{ outline: 0; }}
QWidget {{ color: {t['text_primary']}; font-size: 13px; }}
#Root, QScrollArea, #SettingsBody {{ background: {t['background']}; border: none; }}
{frame}

#TitleBar {{ background: transparent; }}
QLabel#WindowTitle {{ font-size: 13px; font-weight: 600; }}
QToolButton#ChromeButton, QToolButton#CloseButton {{ border-radius: {r['sm']}px; padding: 0; }}
QToolButton#CloseButton:hover, QToolButton#CloseButton:pressed {{ background: {t['error']}; }}

QLabel#Hero {{ font-size: 15px; font-weight: 600; }}
QLabel[role="secondary"] {{ color: {t['text_secondary']}; font-size: 12px; }}
QLabel[role="muted"] {{ color: {t['text_muted']}; font-size: 12px; }}
QLabel[role="section"] {{ color: {t['text_muted']}; font-size: 11px; font-weight: 600; }}
QLabel[role="value"] {{ color: {t['text_secondary']}; font-size: 12px; }}

#Card {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: {r['lg']}px; }}
#Divider {{ background: {t['border']}; max-height: 1px; min-height: 1px; border: none; }}

QComboBox {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: {r['md']}px;
    padding: 0 6px 0 10px; min-height: 30px; combobox-popup: 0;
}}
QComboBox:hover {{ border-color: {t['border_hover']}; }}
QComboBox:on {{ border-color: {t['primary']}; }}
QComboBox[kbfocus="true"] {{ border: 2px solid {t['focus']}; padding: 0 5px 0 9px; }}
QComboBox:disabled {{ color: {t['text_muted']}; background: {t['surface_subtle']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: url("{chevron}"); width: 14px; height: 14px; }}
QComboBoxPrivateContainer {{ background: transparent; border: none; padding: 0; margin: 0; }}
QComboBox QAbstractItemView {{
    background: {t['surface_elevated']}; border: 1px solid {t['border_hover']}; border-radius: {r['md']}px;
    padding: 4px; outline: 0;
    selection-background-color: {t['primary_subtle']}; selection-color: {t['text_primary']};
}}
QComboBox QAbstractItemView::item {{
    min-height: 28px; padding: 0 8px; border: none; border-radius: {r['sm']}px; color: {t['text_primary']};
}}
QComboBox QAbstractItemView::item:hover {{ background: {t['surface_hover']}; }}
QComboBox QAbstractItemView::item:selected {{ background: {t['primary_subtle']}; }}

QPushButton {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: {r['md']}px;
    padding: 0 12px; min-height: 28px; font-weight: 500;
}}
QPushButton:hover {{ background: {t['surface_hover']}; border-color: {t['border_hover']}; }}
QPushButton:pressed {{ background: {t['border']}; }}
QPushButton[kbfocus="true"] {{ border: 2px solid {t['focus']}; padding: 0 11px; }}
QPushButton:disabled {{ color: {t['text_muted']}; background: {t['surface_subtle']}; }}
QPushButton[kind="primary"] {{ background: {t['primary']}; color: {t['on_primary']}; border: none; }}
QPushButton[kind="primary"]:hover {{ background: {t['primary_hover']}; }}
QPushButton[kind="primary"][kbfocus="true"] {{ border: 2px solid {t['text_primary']}; }}
QPushButton[kind="ghost"] {{
    background: transparent; border: none; color: {t['primary']}; padding: 0 2px; min-width: 0; min-height: 18px;
    text-align: left; font-size: 12px;
}}
QPushButton[kind="ghost"]:hover {{ text-decoration: underline; }}
QPushButton[kind="ghost"][kbfocus="true"] {{ border: 2px solid {t['focus']}; padding: 0; }}

QToolButton {{ background: transparent; border: none; border-radius: {r['md']}px; padding: 4px; }}
QToolButton:hover {{ background: {t['surface_hover']}; }}
QToolButton:pressed {{ background: {t['border']}; }}
QToolButton[kbfocus="true"] {{ border: 2px solid {t['focus']}; padding: 2px; }}

QSlider {{ min-height: 20px; }}
QSlider::groove:horizontal {{ height: 4px; background: {t['surface_subtle']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {t['primary']}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {t['surface']}; border: 2px solid {t['primary']};
    width: 12px; height: 12px; margin: -6px 0; border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{ background: {t['primary_subtle']}; }}
QSlider[kbfocus="true"]::handle:horizontal {{ border: 3px solid {t['focus']}; }}
QSlider::sub-page:horizontal:disabled {{ background: {t['border_hover']}; }}
QSlider::handle:horizontal:disabled {{ border-color: {t['border_hover']}; }}

#Banner {{ border-radius: {r['md'] + 2}px; border: 1px solid {t['border']}; background: {t['surface']}; }}
#Banner[kind="success"] {{ background: {t['success_subtle']}; border-color: transparent; }}
#Banner[kind="warning"] {{ background: {t['warning_subtle']}; border-color: transparent; }}
#Banner[kind="error"] {{ background: {t['error_subtle']}; border-color: transparent; }}
#Banner QLabel#BannerTitle {{ font-weight: 600; font-size: 13px; }}

QProgressBar {{ background: {t['surface_subtle']}; border: none; border-radius: 2px; max-height: 4px; }}
QProgressBar::chunk {{ background: {t['primary']}; border-radius: 2px; }}

QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {t['border_hover']}; border-radius: 2px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QToolTip {{
    background: {t['text_primary']}; color: {t['background']}; border: none;
    padding: 4px 7px; border-radius: {r['sm']}px; font-size: 12px;
}}
QMenu {{
    background: {t['surface_elevated']}; border: 1px solid {t['border']}; border-radius: {r['md']}px; padding: 4px;
}}
QMenu::item {{ padding: 6px 20px 6px 10px; border-radius: {r['sm']}px; }}
QMenu::item:selected {{ background: {t['surface_hover']}; }}
QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 6px; }}
"""


def native_frame(widget, t):
    """Give our frameless window back what Windows normally adds: a taskbar button, minimising
    from the taskbar, and DWM's rounded corners, border and shadow. Returns False elsewhere,
    where the stylesheet draws a plain border instead."""
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes

    hwnd = int(widget.winId())
    user32, dwm = ctypes.windll.user32, ctypes.windll.dwmapi
    GWL_STYLE, GWL_EXSTYLE = -16, -20
    WS_MINIMIZEBOX, WS_SYSMENU, WS_EX_APPWINDOW, WS_EX_TOOLWINDOW = 0x20000, 0x80000, 0x40000, 0x80
    user32.SetWindowLongW(hwnd, GWL_STYLE, user32.GetWindowLongW(hwnd, GWL_STYLE) | WS_MINIMIZEBOX | WS_SYSMENU)
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (ex | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW)
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027)  # NOMOVE | NOSIZE | NOZORDER | FRAMECHANGED

    def attr(name, value):
        v = ctypes.c_uint(value)
        return dwm.DwmSetWindowAttribute(hwnd, name, ctypes.byref(v), ctypes.sizeof(v))

    attr(33, 2)  # DWMWA_WINDOW_CORNER_PREFERENCE = DWMWCP_ROUND (Windows 11; ignored before)
    c = t["border_hover"].lstrip("#")
    attr(34, int(c[4:6] + c[2:4] + c[0:2], 16))  # DWMWA_BORDER_COLOR, as COLORREF (0x00BBGGRR)

    class MARGINS(ctypes.Structure):
        _fields_ = [("l", wintypes.INT), ("r", wintypes.INT), ("t", wintypes.INT), ("b", wintypes.INT)]
    dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(MARGINS(0, 0, 0, 1)))  # makes DWM draw the shadow
    return True


def animations_enabled():
    """Honour the OS 'reduce motion' setting where we can read it."""
    if sys.platform == "win32":
        import ctypes
        on = ctypes.c_bool(True)
        ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(on), 0)  # SPI_GETCLIENTAREAANIMATION
        return bool(on.value)
    return True

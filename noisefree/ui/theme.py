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
    path = os.path.join(tempfile.gettempdir(), f"noisefree-chevron-{color.strip('#')}.png")
    if not os.path.exists(path):
        icons.pixmap("chevron", color, 16, dpr=2).save(path)
    return path.replace("\\", "/")


def stylesheet(t):
    r = RADIUS
    chevron = _chevron_file(t["text_secondary"])
    return f"""
* {{ outline: 0; }}
QWidget {{ color: {t['text_primary']}; font-size: 14px; }}
#Root, QScrollArea, #SettingsBody {{ background: {t['background']}; border: none; }}

QLabel#AppName {{ font-size: 16px; font-weight: 600; }}
QLabel#Hero {{ font-size: 20px; font-weight: 600; }}
QLabel#PageTitle {{ font-size: 16px; font-weight: 600; }}
QLabel[role="secondary"] {{ color: {t['text_secondary']}; font-size: 13px; }}
QLabel[role="muted"] {{ color: {t['text_muted']}; font-size: 12px; }}
QLabel[role="section"] {{ color: {t['text_muted']}; font-size: 12px; font-weight: 600; }}
QLabel[role="value"] {{ color: {t['text_secondary']}; font-size: 13px; }}
QLabel[role="link"] {{ color: {t['primary']}; font-size: 13px; }}

#Card {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: {r['lg']}px; }}
#Divider {{ background: {t['border']}; max-height: 1px; min-height: 1px; border: none; }}

QComboBox {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: {r['md']}px;
    padding: 0 10px 0 12px; min-height: 36px;
}}
QComboBox:hover {{ border-color: {t['border_hover']}; }}
QComboBox[kbfocus="true"] {{ border: 2px solid {t['focus']}; padding: 0 9px 0 11px; }}
QComboBox:disabled {{ color: {t['text_muted']}; background: {t['surface_subtle']}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url("{chevron}"); width: 16px; height: 16px; }}
QComboBox QAbstractItemView {{
    background: {t['surface_elevated']}; border: 1px solid {t['border']}; border-radius: {r['md']}px;
    padding: 4px; selection-background-color: {t['primary_subtle']}; selection-color: {t['text_primary']};
}}
QComboBox QAbstractItemView::item {{ min-height: 32px; padding: 0 8px; border-radius: {r['sm']}px; }}

QPushButton {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: {r['md']}px;
    padding: 0 14px; min-height: 34px; font-weight: 500;
}}
QPushButton:hover {{ background: {t['surface_hover']}; border-color: {t['border_hover']}; }}
QPushButton:pressed {{ background: {t['border']}; }}
QPushButton[kbfocus="true"] {{ border: 2px solid {t['focus']}; padding: 0 13px; }}
QPushButton:disabled {{ color: {t['text_muted']}; background: {t['surface_subtle']}; }}
QPushButton[kind="primary"] {{ background: {t['primary']}; color: {t['on_primary']}; border: none; }}
QPushButton[kind="primary"]:hover {{ background: {t['primary_hover']}; }}
QPushButton[kind="primary"][kbfocus="true"] {{ border: 2px solid {t['text_primary']}; }}
QPushButton[kind="ghost"] {{
    background: transparent; border: none; color: {t['primary']}; padding: 0 2px; min-width: 0; text-align: left;
}}
QPushButton[kind="ghost"]:hover {{ text-decoration: underline; }}
QPushButton[kind="ghost"][kbfocus="true"] {{ border: 2px solid {t['focus']}; padding: 0; }}

QToolButton {{ background: transparent; border: none; border-radius: {r['md']}px; padding: 6px; }}
QToolButton:hover {{ background: {t['surface_hover']}; }}
QToolButton:pressed {{ background: {t['border']}; }}
QToolButton[kbfocus="true"] {{ border: 2px solid {t['focus']}; padding: 4px; }}

QSlider {{ min-height: 24px; }}
QSlider::groove:horizontal {{ height: 4px; background: {t['surface_subtle']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {t['primary']}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {t['surface']}; border: 2px solid {t['primary']};
    width: 14px; height: 14px; margin: -7px 0; border-radius: 9px;
}}
QSlider::handle:horizontal:hover {{ background: {t['primary_subtle']}; }}
QSlider[kbfocus="true"]::handle:horizontal {{ border: 3px solid {t['focus']}; }}
QSlider::sub-page:horizontal:disabled {{ background: {t['border_hover']}; }}
QSlider::handle:horizontal:disabled {{ border-color: {t['border_hover']}; }}

#Banner {{ border-radius: 12px; border: 1px solid {t['border']}; background: {t['surface']}; }}
#Banner[kind="success"] {{ background: {t['success_subtle']}; border-color: transparent; }}
#Banner[kind="warning"] {{ background: {t['warning_subtle']}; border-color: transparent; }}
#Banner[kind="error"] {{ background: {t['error_subtle']}; border-color: transparent; }}
#Banner QLabel#BannerTitle {{ font-weight: 600; font-size: 14px; }}

QProgressBar {{ background: {t['surface_subtle']}; border: none; border-radius: 2px; max-height: 4px; }}
QProgressBar::chunk {{ background: {t['primary']}; border-radius: 2px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {t['border_hover']}; border-radius: 3px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

QToolTip {{
    background: {t['text_primary']}; color: {t['background']}; border: none;
    padding: 5px 8px; border-radius: {r['sm']}px; font-size: 12px;
}}
QMenu {{
    background: {t['surface_elevated']}; border: 1px solid {t['border']}; border-radius: {r['md']}px; padding: 4px;
}}
QMenu::item {{ padding: 7px 20px 7px 12px; border-radius: {r['sm']}px; }}
QMenu::item:selected {{ background: {t['surface_hover']}; }}
QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 6px; }}
"""


def set_title_bar_dark(widget, dark):
    """Match the Windows title bar to the theme (no-op elsewhere)."""
    if sys.platform != "win32":
        return
    import ctypes
    value = ctypes.c_int(1 if dark else 0)
    hwnd = int(widget.winId())
    for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (new, then pre-20H1)
        if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
            break


def animations_enabled():
    """Honour the OS 'reduce motion' setting where we can read it."""
    if sys.platform == "win32":
        import ctypes
        on = ctypes.c_bool(True)
        ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(on), 0)  # SPI_GETCLIENTAREAANIMATION
        return bool(on.value)
    return True

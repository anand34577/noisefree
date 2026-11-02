import sys

from PySide6.QtCore import Qt
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from .resources import APP_ID, APP_NAME
from .ui import icons

SERVER_NAME = f"{APP_ID}.single-instance"


def _already_running():
    """If another copy is open, ask it to show its window and return True."""
    sock = QLocalSocket()
    sock.connectToServer(SERVER_NAME)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.waitForBytesWritten(300)
        return True
    return False


def main():
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)  # own taskbar icon

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setEffectEnabled(Qt.UI_AnimateCombo, False)  # the OS fade makes dropdowns look smeared
    app.setWindowIcon(icons.app_icon())
    app.setQuitOnLastWindowClosed(False)  # the tray keeps us alive

    if _already_running():
        return 0

    from .ui.window import MainWindow  # heavy imports (onnxruntime, PortAudio) after the instance check
    win = MainWindow(start_hidden="--minimized" in sys.argv)

    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    server.listen(SERVER_NAME)
    server.newConnection.connect(lambda: (server.nextPendingConnection(), win.show_window()))

    return app.exec()

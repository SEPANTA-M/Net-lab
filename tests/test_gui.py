"""GUI Smoke Test verifying MainWindow structure if Qt OpenGL dependencies are present."""

import os
import pytest

# Check if PySide6 GUI libraries (e.g. libGL) are available in this environment
try:
    from PySide6.QtWidgets import QApplication
    from app.main_window import MainWindow
    HAS_QT_LIB = True
except (ImportError, OSError):
    HAS_QT_LIB = False

# Run Qt offscreen in headless test environments
os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    if not HAS_QT_LIB:
        pytest.skip("PySide6 GUI shared libraries (e.g. libGL.so.1) not present in headless sandbox")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_init(qapp):
    win = MainWindow()
    assert win.windowTitle().startswith("Network Lab")
    assert win.sidebar.count() == 7
    assert win.pages.count() == 7


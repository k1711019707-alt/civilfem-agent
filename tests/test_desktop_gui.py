import os

import pytest


def test_desktop_module_has_clear_qt_entrypoint():
    module = pytest.importorskip("desktop_gui")
    assert hasattr(module, "main")
    assert hasattr(module, "DesktopWindow") == module.QT_AVAILABLE


@pytest.mark.skipif(os.environ.get("CI") == "true", reason="Qt offscreen smoke is local-only")
def test_desktop_window_offscreen(monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from desktop_gui import DesktopWindow

    app = QApplication.instance() or QApplication([])
    window = DesktopWindow(".")
    assert window.windowTitle().startswith("CivilFEM")
    assert len(window.steps) == 5
    assert window.viewport_status.text() == "等待导入图纸"
    assert "background: #08111f" in window.styleSheet()
    window.close()
    app.quit()

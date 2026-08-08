from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from npv_studio.core.settings import DEFAULT_SETTINGS_PATH, load_settings
from npv_studio.ui.main_window import MainWindow


def run_gui(settings_path: Path = DEFAULT_SETTINGS_PATH) -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("NPV Studio")
    application.setOrganizationName("NPV Studio")
    window = MainWindow(load_settings(settings_path), settings_path=settings_path)
    window.show()
    return application.exec()

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from hyperdesk.core.controller import AppController
from hyperdesk.ui.app_state import AppState
from hyperdesk.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    state = AppState()
    controller = AppController(state)
    window = MainWindow(state, controller)
    window.show()
    app.aboutToQuit.connect(controller.shutdown)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

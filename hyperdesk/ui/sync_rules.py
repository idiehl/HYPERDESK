from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
)


class SyncRulesDialog(QDialog):
    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Sync Rules")

        self.mode = QComboBox()
        self.mode.addItems(["mirror", "copy", "approval"])

        self.conflict_rule = QComboBox()
        self.conflict_rule.addItems(["keep_both", "prefer_host", "prefer_peer"])

        self._load()

        form = QFormLayout()
        form.addRow("Mode:", self.mode)
        form.addRow("Conflict rule:", self.conflict_rule)

        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(self._save)
        cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(buttons)
        self.setLayout(layout)

    def _load(self) -> None:
        session = self.controller.state.session
        if not session:
            return
        self.mode.setCurrentText(session.policy.mode)
        self.conflict_rule.setCurrentText(session.policy.conflict_rule)

    def _save(self) -> None:
        self.controller.update_sync_rules(
            self.mode.currentText(),
            self.conflict_rule.currentText(),
        )
        self.accept()

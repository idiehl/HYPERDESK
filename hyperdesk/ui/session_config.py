from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
)


class SessionConfigDialog(QDialog):
    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Session Configuration (Host)")

        self.mode = QComboBox()
        self.mode.addItems(["mirror", "copy", "approval"])

        self.conflict_rule = QComboBox()
        self.conflict_rule.addItems(["keep_both", "prefer_host", "prefer_peer"])

        self.allow_browse = QCheckBox("Allow client browse")
        self.allow_requests = QCheckBox("Allow client requests")
        self.allow_edits = QCheckBox("Allow client edits")
        self.allow_client_share = QCheckBox("Allow client share")

        self.edit_mode = QComboBox()
        self.edit_mode.addItems(["copy_on_edit", "in_place"])

        self._load()

        form = QFormLayout()
        form.addRow("Mode:", self.mode)
        form.addRow("Conflict rule:", self.conflict_rule)
        form.addRow(self.allow_browse)
        form.addRow(self.allow_requests)
        form.addRow(self.allow_edits)
        form.addRow("Edit mode:", self.edit_mode)
        form.addRow(self.allow_client_share)

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
        config = self.controller.get_default_session_config()
        self.mode.setCurrentText(config["mode"])
        self.conflict_rule.setCurrentText(config["conflict_rule"])
        self.allow_browse.setChecked(config["allow_browse"])
        self.allow_requests.setChecked(config["allow_requests"])
        self.allow_edits.setChecked(config["allow_edits"])
        self.edit_mode.setCurrentText(config["edit_mode"])
        self.allow_client_share.setChecked(config["allow_client_share"])

    def _save(self) -> None:
        config = {
            "mode": self.mode.currentText(),
            "conflict_rule": self.conflict_rule.currentText(),
            "allow_browse": self.allow_browse.isChecked(),
            "allow_requests": self.allow_requests.isChecked(),
            "allow_edits": self.allow_edits.isChecked(),
            "edit_mode": self.edit_mode.currentText(),
            "allow_client_share": self.allow_client_share.isChecked(),
        }
        self.controller.save_default_session_config(config)
        self.accept()

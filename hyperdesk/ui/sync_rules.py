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


class SyncRulesDialog(QDialog):
    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Sync Rules")

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
        session = self.controller.state.session
        if not session:
            return
        self.mode.setCurrentText(session.policy.mode)
        self.conflict_rule.setCurrentText(session.policy.conflict_rule)
        self.allow_browse.setChecked(session.policy.allow_browse)
        self.allow_requests.setChecked(session.policy.allow_requests)
        self.allow_edits.setChecked(session.policy.allow_edits)
        self.edit_mode.setCurrentText(session.policy.edit_mode)
        self.allow_client_share.setChecked(session.policy.allow_client_share)

    def _save(self) -> None:
        self.controller.update_sync_rules(
            self.mode.currentText(),
            self.conflict_rule.currentText(),
            self.allow_browse.isChecked(),
            self.allow_requests.isChecked(),
            self.allow_edits.isChecked(),
            self.edit_mode.currentText(),
            self.allow_client_share.isChecked(),
        )
        self.accept()

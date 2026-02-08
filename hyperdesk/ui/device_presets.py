from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
)


class DevicePresetsDialog(QDialog):
    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Device Sync Presets")

        self.device_selector = QComboBox()
        self.mode = QComboBox()
        self.mode.addItems(["mirror", "copy", "approval"])

        self.conflict_rule = QComboBox()
        self.conflict_rule.addItems(["keep_both", "prefer_host", "prefer_peer"])

        self._load_devices()

        form = QFormLayout()
        form.addRow("Device:", self.device_selector)
        form.addRow("Mode:", self.mode)
        form.addRow("Conflict rule:", self.conflict_rule)

        save_button = QPushButton("Save")
        close_button = QPushButton("Close")
        save_button.clicked.connect(self._save)
        close_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(save_button)
        buttons.addWidget(close_button)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(buttons)
        self.setLayout(layout)

        self.device_selector.currentIndexChanged.connect(self._load_preset)
        self._load_preset()

    def _load_devices(self) -> None:
        self.device_selector.clear()
        devices = self.controller.list_devices()
        for device in devices:
            label = f"{device['name']} ({device['ip']})"
            self.device_selector.addItem(label, device["id"])

    def _load_preset(self) -> None:
        device_id = self.device_selector.currentData()
        if not device_id:
            return
        mode, conflict_rule = self.controller.get_device_sync_preset(device_id)
        self.mode.setCurrentText(mode)
        self.conflict_rule.setCurrentText(conflict_rule)

    def _save(self) -> None:
        device_id = self.device_selector.currentData()
        if not device_id:
            return
        self.controller.set_device_sync_preset(
            device_id,
            self.mode.currentText(),
            self.conflict_rule.currentText(),
        )

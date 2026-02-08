from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


class TransferSettingsDialog(QDialog):
    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Transfer Settings")

        self.chunk_size = QSpinBox()
        self.chunk_size.setRange(1, 512)
        self.chunk_size.setSuffix(" MB")

        self.max_bandwidth = QComboBox()
        self.max_bandwidth.addItems(
            ["unlimited", "10 MB/s", "25 MB/s", "50 MB/s", "100 MB/s"]
        )

        self.retry_policy = QComboBox()
        self.retry_policy.addItems(["exponential", "linear", "none"])

        self.max_retries = QSpinBox()
        self.max_retries.setRange(0, 20)

        self.encryption = QCheckBox("Encrypt transfers (AES-256)")

        self._load_settings()

        form = QFormLayout()
        form.addRow("Chunk size:", self.chunk_size)
        form.addRow("Max bandwidth:", self.max_bandwidth)
        form.addRow("Retry policy:", self.retry_policy)
        form.addRow("Max retries:", self.max_retries)
        form.addRow("", self.encryption)

        save_button = QPushButton("Save")
        reset_button = QPushButton("Reset")
        save_button.clicked.connect(self._save)
        reset_button.clicked.connect(self._reset)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(save_button)
        buttons.addWidget(reset_button)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(buttons)
        self.setLayout(layout)

    def _load_settings(self) -> None:
        settings = self.controller.get_transfer_settings()
        self.chunk_size.setValue(settings["chunk_size_mb"])
        self.max_bandwidth.setCurrentText(settings["max_bandwidth"])
        self.retry_policy.setCurrentText(settings["retry_policy"])
        self.max_retries.setValue(settings["max_retries"])
        self.encryption.setChecked(settings["encryption"])

    def _save(self) -> None:
        settings = {
            "chunk_size_mb": self.chunk_size.value(),
            "max_bandwidth": self.max_bandwidth.currentText(),
            "retry_policy": self.retry_policy.currentText(),
            "max_retries": self.max_retries.value(),
            "encryption": self.encryption.isChecked(),
        }
        self.controller.save_transfer_settings(settings)
        self.accept()

    def _reset(self) -> None:
        self.controller.save_transfer_settings(
            {
                "chunk_size_mb": 8,
                "max_bandwidth": "unlimited",
                "retry_policy": "exponential",
                "max_retries": 3,
                "encryption": False,
            }
        )
        self._load_settings()

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)


class PairingOfferDialog(QDialog):
    def __init__(self, controller, offer: dict, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.offer = offer
        self.setWindowTitle("Connection Request")

        form = QFormLayout()
        form.addRow("Host:", QLabel(f"{offer.get('host_name')} ({offer.get('host_ip')})"))
        form.addRow("Mode:", QLabel(str(offer.get("mode"))))
        form.addRow("Conflict:", QLabel(str(offer.get("conflict_rule"))))
        form.addRow("Allow browse:", QLabel(str(offer.get("allow_browse"))))
        form.addRow("Allow requests:", QLabel(str(offer.get("allow_requests"))))
        form.addRow("Allow edits:", QLabel(str(offer.get("allow_edits"))))
        form.addRow("Edit mode:", QLabel(str(offer.get("edit_mode"))))
        form.addRow(
            "Allow client share:", QLabel(str(offer.get("allow_client_share")))
        )

        accept_button = QPushButton("Accept")
        decline_button = QPushButton("Decline")
        accept_button.clicked.connect(self._accept)
        decline_button.clicked.connect(self._decline)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(accept_button)
        buttons.addWidget(decline_button)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(buttons)
        self.setLayout(layout)

    def _accept(self) -> None:
        self.controller.accept_pairing_offer()
        self.accept()

    def _decline(self) -> None:
        self.controller.decline_pairing_offer()
        self.reject()

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hyperdesk.core.models import Device, FileRequest, Session, TransferJob
from hyperdesk.ui.request_queue import RequestQueueDialog
from hyperdesk.ui.sync_rules import SyncRulesDialog
from hyperdesk.ui.transfer_settings import TransferSettingsDialog


class MainWindow(QMainWindow):
    def __init__(self, state, controller) -> None:
        super().__init__()
        self.state = state
        self.controller = controller

        self.device_list = QListWidget()
        self.scan_button = QPushButton("Scan")
        self.start_pairing_button = QPushButton("Start Pairing")
        self.link_button = QPushButton("Link")
        self.disconnect_button = QPushButton("Disconnect")
        self.simulate_button = QPushButton("Simulate Transfer")
        self.simulate_request_button = QPushButton("Simulate Request")
        self.settings_button = QPushButton("Transfer Settings")
        self.request_queue_button = QPushButton("Request Queue")
        self.sync_rules_button = QPushButton("Sync Rules")
        self.pairing_label = QLabel("Pairing code: --")
        self.session_status = QLabel("--")
        self.session_peer = QLabel("--")
        self.session_mode = QLabel("--")
        self.session_conflict = QLabel("--")
        self.transfer_table = QTableWidget(0, 5)
        self.request_table = QTableWidget(0, 4)
        self.log_view = QTextEdit()

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        self.setWindowTitle("HYPERDESK")
        self.resize(900, 600)

        header = QLabel("HYPERDESK")
        header.setStyleSheet("font-size: 22px; font-weight: bold;")

        button_row = QHBoxLayout()
        button_row.addWidget(self.scan_button)
        button_row.addWidget(self.start_pairing_button)
        button_row.addWidget(self.link_button)
        button_row.addWidget(self.disconnect_button)
        button_row.addWidget(self.simulate_button)
        button_row.addWidget(self.simulate_request_button)
        button_row.addWidget(self.settings_button)
        button_row.addWidget(self.request_queue_button)
        button_row.addWidget(self.sync_rules_button)
        button_row.addStretch()

        device_box = QGroupBox("Devices")
        device_layout = QVBoxLayout()
        device_layout.addWidget(self.device_list)
        device_box.setLayout(device_layout)

        session_box = QGroupBox("Session Details")
        session_layout = QFormLayout()
        session_layout.addRow("Status:", self.session_status)
        session_layout.addRow("Peer device:", self.session_peer)
        session_layout.addRow("Mode:", self.session_mode)
        session_layout.addRow("Conflict rule:", self.session_conflict)
        session_layout.addRow(self.pairing_label)
        session_box.setLayout(session_layout)

        transfer_box = QGroupBox("Transfer Log")
        self.transfer_table.setHorizontalHeaderLabels(
            ["File", "Direction", "Progress", "Status", "Rate"]
        )
        self.transfer_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.transfer_table.verticalHeader().setVisible(False)
        self.transfer_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        transfer_layout = QVBoxLayout()
        transfer_layout.addWidget(self.transfer_table)
        self.transfer_footer = QLabel("Active: 0 | Avg rate: -- | Limit: --")
        transfer_layout.addWidget(self.transfer_footer)
        transfer_box.setLayout(transfer_layout)

        request_box = QGroupBox("Request Queue")
        self.request_table.setHorizontalHeaderLabels(
            ["File", "Requester", "Status", "Actions"]
        )
        self.request_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.request_table.verticalHeader().setVisible(False)
        self.request_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        request_layout = QVBoxLayout()
        request_layout.addWidget(self.request_table)
        request_box.setLayout(request_layout)

        main_row = QHBoxLayout()
        main_row.addWidget(device_box, 2)
        main_row.addWidget(session_box, 3)

        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Log output will appear here.")

        root_layout = QVBoxLayout()
        root_layout.addWidget(header)
        root_layout.addLayout(button_row)
        root_layout.addLayout(main_row)
        root_layout.addWidget(request_box)
        root_layout.addWidget(transfer_box)
        root_layout.addWidget(self.log_view)

        container = QWidget()
        container.setLayout(root_layout)
        self.setCentralWidget(container)

        self.link_button.setEnabled(False)
        self.disconnect_button.setEnabled(False)
        self.simulate_button.setEnabled(False)
        self.simulate_request_button.setEnabled(False)

    def _connect_signals(self) -> None:
        self.scan_button.clicked.connect(self.controller.scan)
        self.start_pairing_button.clicked.connect(self.controller.start_pairing)
        self.link_button.clicked.connect(self._handle_link)
        self.disconnect_button.clicked.connect(self.controller.disconnect)
        self.simulate_button.clicked.connect(self.controller.simulate_transfer)
        self.simulate_request_button.clicked.connect(self.controller.simulate_request)
        self.settings_button.clicked.connect(self._open_settings)
        self.request_queue_button.clicked.connect(self._open_request_queue)
        self.sync_rules_button.clicked.connect(self._open_sync_rules)

        self.state.devices_changed.connect(self._update_devices)
        self.state.session_changed.connect(self._update_session)
        self.state.pairing_changed.connect(self._update_pairing)
        self.state.log_added.connect(self._append_log)
        self.state.transfers_changed.connect(self._update_transfers)
        self.state.requests_changed.connect(self._update_requests)

    def _handle_link(self) -> None:
        item = self.device_list.currentItem()
        if not item:
            self.state.add_log("Select a device before linking.")
            return
        device = item.data(Qt.UserRole)
        if isinstance(device, Device):
            self.controller.link_to_device(device)

    def _update_devices(self, devices: list[Device]) -> None:
        self.device_list.clear()
        for device in devices:
            item = QListWidgetItem(f"{device.name} ({device.ip})")
            item.setData(Qt.UserRole, device)
            self.device_list.addItem(item)
        self.link_button.setEnabled(bool(devices))

    def _update_session(self, session: Session | None) -> None:
        if session is None:
            self.session_status.setText("--")
            self.session_peer.setText("--")
            self.session_mode.setText("--")
            self.session_conflict.setText("--")
            self.disconnect_button.setEnabled(False)
            self.simulate_button.setEnabled(False)
            self.simulate_request_button.setEnabled(False)
            return
        self.session_status.setText(session.status)
        self.session_peer.setText(session.peer_device.name)
        self.session_mode.setText(session.policy.mode)
        self.session_conflict.setText(session.policy.conflict_rule)
        self.disconnect_button.setEnabled(True)
        self.simulate_button.setEnabled(True)
        self.simulate_request_button.setEnabled(True)

    def _update_pairing(self, code: str) -> None:
        self.pairing_label.setText(f"Pairing code: {code or '--'}")

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)

    def _update_transfers(self, transfers: list[TransferJob]) -> None:
        self.transfer_table.setRowCount(len(transfers))
        for row, job in enumerate(transfers):
            file_name = Path(job.path).name
            self.transfer_table.setItem(row, 0, QTableWidgetItem(file_name))
            self.transfer_table.setItem(row, 1, QTableWidgetItem(job.direction))

            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(int(job.progress * 100))
            self.transfer_table.setCellWidget(row, 2, progress_bar)

            status_item = QTableWidgetItem(job.status)
            self.transfer_table.setItem(row, 3, status_item)

            rate_text = f"{job.rate_mbps:.2f} MB/s" if job.rate_mbps else "--"
            self.transfer_table.setItem(row, 4, QTableWidgetItem(rate_text))
        self._update_transfer_footer(transfers)

    def _update_transfer_footer(self, transfers: list[TransferJob]) -> None:
        active = [
            job
            for job in transfers
            if job.status in ("transferring", "receiving", "sending")
        ]
        rates = [job.rate_mbps for job in active if job.rate_mbps > 0]
        avg_rate = sum(rates) / len(rates) if rates else 0.0
        limit_mbps = self.controller.get_transfer_limit_mbps()
        limit_text = f"{limit_mbps:.2f} MB/s" if limit_mbps else "unlimited"
        util_text = (
            f"{(avg_rate / limit_mbps) * 100:.0f}%"
            if limit_mbps and avg_rate
            else "--"
        )
        self.transfer_footer.setText(
            f"Active: {len(active)} | Avg rate: {avg_rate:.2f} MB/s | Limit: {limit_text} | Util: {util_text}"
        )

    def _update_requests(self, requests: list[FileRequest]) -> None:
        self.request_table.setRowCount(len(requests))
        for row, request in enumerate(requests):
            file_name = Path(request.path).name
            self.request_table.setItem(row, 0, QTableWidgetItem(file_name))
            self.request_table.setItem(row, 1, QTableWidgetItem(request.requester))
            self.request_table.setItem(row, 2, QTableWidgetItem(request.status))

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            approve_button = QPushButton("Approve")
            decline_button = QPushButton("Decline")
            is_pending = request.status == "pending"
            approve_button.setEnabled(is_pending)
            decline_button.setEnabled(is_pending)
            approve_button.clicked.connect(
                lambda _checked=False, req_id=request.id: self._approve_request(req_id)
            )
            decline_button.clicked.connect(
                lambda _checked=False, req_id=request.id: self.controller.decline_request(
                    req_id
                )
            )
            action_layout.addWidget(approve_button)
            action_layout.addWidget(decline_button)
            self.request_table.setCellWidget(row, 3, action_widget)

    def _open_settings(self) -> None:
        dialog = TransferSettingsDialog(self.controller, self)
        dialog.exec()

    def _approve_request(self, request_id: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select source file to send",
            "",
        )
        if not path:
            return
        self.controller.approve_request_with_source(request_id, path)

    def _open_request_queue(self) -> None:
        dialog = RequestQueueDialog(self.controller, self)
        dialog.exec()

    def _open_sync_rules(self) -> None:
        dialog = SyncRulesDialog(self.controller, self)
        dialog.exec()

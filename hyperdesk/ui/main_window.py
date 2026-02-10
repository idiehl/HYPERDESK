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
    QLineEdit,
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
from hyperdesk.ui.bandwidth_history import BandwidthHistoryDialog
from hyperdesk.ui.device_presets import DevicePresetsDialog
from hyperdesk.ui.pairing_offer import PairingOfferDialog
from hyperdesk.ui.request_queue import RequestQueueDialog
from hyperdesk.ui.session_config import SessionConfigDialog
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
        self.share_button = QPushButton("Share File")
        self.settings_button = QPushButton("Transfer Settings")
        self.request_queue_button = QPushButton("Request Queue")
        self.sync_rules_button = QPushButton("Sync Rules")
        self.bandwidth_button = QPushButton("Bandwidth History")
        self.device_presets_button = QPushButton("Device Presets")
        self.session_config_button = QPushButton("Session Config")
        self.connect_host_button = QPushButton("Connect to Host")
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("Host IP (e.g. 192.168.1.10)")
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Pairing code")
        self.request_path_input = QLineEdit()
        self.request_path_input.setPlaceholderText("Request path (e.g. /Docs/report.pdf)")
        self.request_file_button = QPushButton("Request File")
        self.browse_host_button = QPushButton("Browse Host")
        self.pairing_label = QLabel("Pairing code: --")
        self.session_status = QLabel("--")
        self.session_peer = QLabel("--")
        self.session_mode = QLabel("--")
        self.session_conflict = QLabel("--")
        self.session_access = QLabel("--")
        self.session_role = QLabel("--")
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
        button_row.addWidget(self.share_button)
        button_row.addWidget(self.settings_button)
        button_row.addWidget(self.request_queue_button)
        button_row.addWidget(self.sync_rules_button)
        button_row.addWidget(self.bandwidth_button)
        button_row.addWidget(self.device_presets_button)
        button_row.addWidget(self.session_config_button)
        button_row.addStretch()

        connection_box = QGroupBox("Connect (Client)")
        connection_layout = QHBoxLayout()
        connection_layout.addWidget(self.host_input)
        connection_layout.addWidget(self.code_input)
        connection_layout.addWidget(self.connect_host_button)
        connection_box.setLayout(connection_layout)

        client_actions = QGroupBox("Client Actions")
        client_layout = QHBoxLayout()
        client_layout.addWidget(self.request_path_input)
        client_layout.addWidget(self.request_file_button)
        client_layout.addWidget(self.browse_host_button)
        client_actions.setLayout(client_layout)

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
        session_layout.addRow("Access:", self.session_access)
        session_layout.addRow("Role:", self.session_role)
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
        root_layout.addWidget(connection_box)
        root_layout.addWidget(client_actions)
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
        self.share_button.clicked.connect(self._share_file)
        self.settings_button.clicked.connect(self._open_settings)
        self.request_queue_button.clicked.connect(self._open_request_queue)
        self.sync_rules_button.clicked.connect(self._open_sync_rules)
        self.bandwidth_button.clicked.connect(self._open_bandwidth_history)
        self.device_presets_button.clicked.connect(self._open_device_presets)
        self.session_config_button.clicked.connect(self._open_session_config)
        self.connect_host_button.clicked.connect(self._connect_to_host)
        self.request_file_button.clicked.connect(self._request_file)
        self.browse_host_button.clicked.connect(self._browse_host)

        self.state.devices_changed.connect(self._update_devices)
        self.state.session_changed.connect(self._update_session)
        self.state.pairing_changed.connect(self._update_pairing)
        self.state.log_added.connect(self._append_log)
        self.state.transfers_changed.connect(self._update_transfers)
        self.state.requests_changed.connect(self._update_requests)
        self.state.pairing_offer_changed.connect(self._handle_pairing_offer)

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
            self.session_access.setText("--")
            self.session_role.setText("--")
            self.disconnect_button.setEnabled(False)
            self.simulate_button.setEnabled(False)
            self.simulate_request_button.setEnabled(False)
            self.share_button.setEnabled(False)
            self.request_file_button.setEnabled(False)
            self.browse_host_button.setEnabled(False)
            return
        self.session_status.setText(session.status)
        self.session_peer.setText(session.peer_device.name)
        self.session_mode.setText(session.policy.mode)
        self.session_conflict.setText(session.policy.conflict_rule)
        access = []
        if session.policy.allow_browse:
            access.append("browse")
        if session.policy.allow_requests:
            access.append("request")
        if session.policy.allow_edits:
            access.append(f"edit:{session.policy.edit_mode}")
        if session.policy.allow_client_share:
            access.append("share")
        self.session_access.setText(", ".join(access) if access else "none")
        role = "host" if session.host_device.id == self.controller.local_device.id else "client"
        self.session_role.setText(role)
        self.disconnect_button.setEnabled(True)
        self.simulate_button.setEnabled(True)
        self.simulate_request_button.setEnabled(True)
        self.share_button.setEnabled(True)
        self.request_file_button.setEnabled(session.policy.allow_requests)
        self.browse_host_button.setEnabled(session.policy.allow_browse)

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
        self.controller.record_bandwidth_sample(avg_rate, limit_mbps)

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

    def _share_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select local file to share",
            "",
        )
        if not path:
            return
        self.controller.share_local_file(Path(path))

    def _open_request_queue(self) -> None:
        dialog = RequestQueueDialog(self.controller, self)
        dialog.exec()

    def _open_sync_rules(self) -> None:
        dialog = SyncRulesDialog(self.controller, self)
        dialog.exec()

    def _open_bandwidth_history(self) -> None:
        dialog = BandwidthHistoryDialog(self.controller, self)
        dialog.exec()

    def _open_device_presets(self) -> None:
        dialog = DevicePresetsDialog(self.controller, self)
        dialog.exec()

    def _open_session_config(self) -> None:
        dialog = SessionConfigDialog(self.controller, self)
        dialog.exec()

    def _connect_to_host(self) -> None:
        host = self.host_input.text().strip()
        code = self.code_input.text().strip()
        if not host or not code:
            self.state.add_log("Enter host IP and pairing code.")
            return
        self.controller.connect_to_host(host, 8765, code)

    def _handle_pairing_offer(self, offer: dict) -> None:
        if not offer:
            return
        dialog = PairingOfferDialog(self.controller, offer, self)
        dialog.exec()

    def _request_file(self) -> None:
        path = self.request_path_input.text().strip()
        if not path:
            self.state.add_log("Enter a remote path to request.")
            return
        self.controller.request_remote_file(path)

    def _browse_host(self) -> None:
        self.state.add_log("Host browsing is not implemented yet.")

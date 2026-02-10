from __future__ import annotations

from datetime import datetime

import csv
import time

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QTimer

from hyperdesk.core.models import FileRequest


class RequestQueueDialog(QDialog):
    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Request Queue")
        self.resize(700, 400)

        self.status_filter = QComboBox()
        self.status_filter.addItems(
            ["all", "pending", "approved", "declined", "in_progress", "completed", "failed", "skipped"]
        )
        self.requester_filter = QComboBox()
        self.requester_filter.addItems(["all", "local", "peer"])
        self.session_filter = QComboBox()
        self.device_filter = QComboBox()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search file name")
        self.refresh_button = QPushButton("Refresh")
        self.export_button = QPushButton("Export CSV")
        self.auto_export = QCheckBox("Auto export")
        self.auto_interval = QSpinBox()
        self.auto_interval.setRange(1, 120)
        self.auto_interval.setSuffix(" min")
        self.auto_path = QLineEdit()
        self.auto_path.setPlaceholderText("Archive folder (optional)")
        self.auto_browse = QPushButton("Browse")
        self._auto_timer = QTimer(self)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Status:"))
        filter_row.addWidget(self.status_filter)
        filter_row.addWidget(QLabel("Requester:"))
        filter_row.addWidget(self.requester_filter)
        filter_row.addWidget(QLabel("Session:"))
        filter_row.addWidget(self.session_filter)
        filter_row.addWidget(QLabel("Device:"))
        filter_row.addWidget(self.device_filter)
        filter_row.addWidget(self.search_box)
        filter_row.addWidget(self.refresh_button)
        filter_row.addWidget(self.export_button)
        filter_row.addWidget(self.auto_export)
        filter_row.addWidget(self.auto_interval)
        filter_row.addWidget(self.auto_path)
        filter_row.addWidget(self.auto_browse)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["File", "Requester", "Status", "Session", "Device", "Created", "Actions"]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        layout = QVBoxLayout()
        layout.addLayout(filter_row)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.status_filter.currentTextChanged.connect(self.refresh)
        self.requester_filter.currentTextChanged.connect(self.refresh)
        self.session_filter.currentTextChanged.connect(self.refresh)
        self.device_filter.currentTextChanged.connect(self.refresh)
        self.search_box.textChanged.connect(self.refresh)
        self.refresh_button.clicked.connect(self.refresh)
        self.export_button.clicked.connect(self.export_csv)
        self.auto_export.toggled.connect(self._toggle_auto_export)
        self.auto_browse.clicked.connect(self._browse_auto_path)
        self._auto_timer.timeout.connect(self._auto_export_tick)

        self.refresh()

    def refresh(self) -> None:
        self._sync_filters()
        requests = self.controller.get_request_history_all()
        filtered = self._apply_filters(requests)
        self.table.setRowCount(len(filtered))
        session_map = self.controller.get_session_index()
        for row, request in enumerate(filtered):
            self.table.setItem(row, 0, QTableWidgetItem(_file_name(request.path)))
            self.table.setItem(row, 1, QTableWidgetItem(request.requester))
            self.table.setItem(row, 2, QTableWidgetItem(request.status))
            self.table.setItem(row, 3, QTableWidgetItem(_short_id(request.session_id)))
            device_name = session_map.get(request.session_id, "Unknown")
            self.table.setItem(row, 4, QTableWidgetItem(device_name))
            created = request.created_at.strftime("%Y-%m-%d %H:%M")
            self.table.setItem(row, 5, QTableWidgetItem(created))

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            approve_button = QPushButton("Approve")
            decline_button = QPushButton("Decline")
            is_pending = request.status == "pending"
            approve_button.setEnabled(is_pending)
            decline_button.setEnabled(is_pending)
            approve_button.clicked.connect(
                lambda _checked=False, req_id=request.id: self._approve(req_id)
            )
            decline_button.clicked.connect(
                lambda _checked=False, req_id=request.id: self.controller.decline_request(
                    req_id
                )
            )
            action_layout.addWidget(approve_button)
            action_layout.addWidget(decline_button)
            self.table.setCellWidget(row, 6, action_widget)

    def _apply_filters(self, requests: list[FileRequest]) -> list[FileRequest]:
        status = self.status_filter.currentText()
        requester = self.requester_filter.currentText()
        session_filter = self.session_filter.currentData()
        device_filter = self.device_filter.currentText()
        search = self.search_box.text().strip().lower()
        session_map = self.controller.get_session_index()

        filtered = []
        for request in requests:
            if status != "all" and request.status != status:
                continue
            if requester != "all" and request.requester != requester:
                continue
            if session_filter and request.session_id != session_filter:
                continue
            if device_filter != "all":
                device_name = session_map.get(request.session_id, "Unknown")
                if device_name != device_filter:
                    continue
            if search and search not in request.path.lower():
                continue
            filtered.append(request)
        return filtered

    def _approve(self, request_id: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select source file to send",
            "",
        )
        if not path:
            return
        self.controller.approve_request_with_source(request_id, path)
        self.refresh()

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export request queue",
            "request_queue.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return
        requests = self._apply_filters(self.controller.get_request_history_all())
        session_map = self.controller.get_session_index()
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["file", "requester", "status", "session_id", "device", "created_at"]
            )
            for request in requests:
                device_name = session_map.get(request.session_id, "Unknown")
                writer.writerow(
                    [
                        request.path,
                        request.requester,
                        request.status,
                        request.session_id,
                        device_name,
                        request.created_at.isoformat(),
                    ]
                )

    def _toggle_auto_export(self, enabled: bool) -> None:
        if enabled:
            self._auto_timer.start(self.auto_interval.value() * 60 * 1000)
            self._auto_export_tick()
        else:
            self._auto_timer.stop()

    def _browse_auto_path(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select export folder")
        if path:
            self.auto_path.setText(path)

    def _auto_export_tick(self) -> None:
        folder = self.auto_path.text().strip() or "."
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = f"{folder}/request_queue_{timestamp}.csv"
        requests = self._apply_filters(self.controller.get_request_history_all())
        session_map = self.controller.get_session_index()
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["file", "requester", "status", "session_id", "device", "created_at"]
            )
            for request in requests:
                device_name = session_map.get(request.session_id, "Unknown")
                writer.writerow(
                    [
                        request.path,
                        request.requester,
                        request.status,
                        request.session_id,
                        device_name,
                        request.created_at.isoformat(),
                    ]
                )

    def _sync_filters(self) -> None:
        session_map = self.controller.get_session_index()
        current_session = self.session_filter.currentData()
        current_device = self.device_filter.currentText()

        self.session_filter.blockSignals(True)
        self.session_filter.clear()
        self.session_filter.addItem("all", None)
        for session_id, device_name in session_map.items():
            label = f"{device_name} ({_short_id(session_id)})"
            self.session_filter.addItem(label, session_id)
        if current_session:
            index = self.session_filter.findData(current_session)
            if index != -1:
                self.session_filter.setCurrentIndex(index)
        self.session_filter.blockSignals(False)

        self.device_filter.blockSignals(True)
        self.device_filter.clear()
        self.device_filter.addItem("all")
        for device_name in sorted({name for name in session_map.values()}):
            self.device_filter.addItem(device_name)
        if current_device:
            index = self.device_filter.findText(current_device)
            if index != -1:
                self.device_filter.setCurrentIndex(index)
        self.device_filter.blockSignals(False)


def _file_name(path: str) -> str:
    return path.split("/")[-1].split("\\")[-1]


def _short_id(value: str) -> str:
    return value[:8]

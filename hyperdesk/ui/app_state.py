from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from hyperdesk.core.models import Device, FileRequest, Session, TransferJob


class AppState(QObject):
    devices_changed = Signal(list)
    session_changed = Signal(object)
    pairing_changed = Signal(str)
    log_added = Signal(str)
    transfers_changed = Signal(list)
    requests_changed = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.devices: List[Device] = []
        self.session: Optional[Session] = None
        self.pairing_code: str = ""
        self.logs: List[str] = []
        self.transfers: List[TransferJob] = []
        self.requests: List[FileRequest] = []

    def set_devices(self, devices: List[Device]) -> None:
        self.devices = devices
        self.devices_changed.emit(devices)

    def set_session(self, session: Optional[Session]) -> None:
        self.session = session
        self.session_changed.emit(session)

    def set_pairing_code(self, code: str) -> None:
        self.pairing_code = code
        self.pairing_changed.emit(code)

    def add_log(self, message: str) -> None:
        self.logs.append(message)
        self.log_added.emit(message)

    def set_transfers(self, transfers: List[TransferJob]) -> None:
        self.transfers = transfers
        self.transfers_changed.emit(transfers)

    def update_transfer(self, job: TransferJob) -> None:
        for index, existing in enumerate(self.transfers):
            if existing.id == job.id:
                self.transfers[index] = job
                self.transfers_changed.emit(self.transfers)
                return
        self.transfers.append(job)
        self.transfers_changed.emit(self.transfers)

    def set_requests(self, requests: List[FileRequest]) -> None:
        self.requests = requests
        self.requests_changed.emit(requests)

from __future__ import annotations

import asyncio
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from hyperdesk.core.hyperbox import HyperboxManager
from hyperdesk.core.models import Device, FileRequest, PairingSession, TransferJob
from hyperdesk.core.requests import RequestQueue
from hyperdesk.core.storage import Storage
from hyperdesk.core.watcher import HyperboxWatcher
from hyperdesk.network.control import ControlServer
from hyperdesk.network.discovery import NetworkDiscovery, ZeroconfService
from hyperdesk.network.pairing import PairingManager
from hyperdesk.network.protocol import encode_message
from hyperdesk.transfer.channel import FileSender
from hyperdesk.transfer.engine import TransferEngine


class AppController:
    def __init__(self, state) -> None:
        self.state = state
        self.discovery = NetworkDiscovery()
        self.pairing = PairingManager()
        self.transfer = TransferEngine()
        self.local_device = _build_local_device()
        self.storage = Storage()
        self.hyperbox = HyperboxManager()
        self.requests = RequestQueue(self.storage)
        self.watcher = HyperboxWatcher(self.hyperbox.root, self._handle_hyperbox_event)
        self._closing = False
        self.pending_pairing: Optional[PairingSession] = None
        self._last_transfer_by_path: dict[str, float] = {}
        self._request_transfer_map: dict[str, str] = {}
        self._transfer_metrics: dict[str, tuple[int, float]] = {}
        self._transfer_defaults = {
            "chunk_size_mb": 8,
            "max_bandwidth": "unlimited",
            "retry_policy": "exponential",
            "max_retries": 3,
            "encryption": False,
        }
        self._control_loop: Optional[asyncio.AbstractEventLoop] = None
        self._control_thread: Optional[threading.Thread] = None
        self.control_server: Optional[ControlServer] = None
        self.control_host = "127.0.0.1"
        self.control_port = 8765
        self.mdns_service: Optional[ZeroconfService] = None

        self.storage.record_device(self.local_device)
        if self.discovery.use_mdns:
            self.mdns_service = ZeroconfService(self.local_device)
            try:
                self.mdns_service.start()
            except Exception:
                self.mdns_service = None
        self.watcher.start()
        self.start_control_server(self.control_host, self.control_port)

    def scan(self) -> None:
        devices = self.discovery.scan()
        devices = _dedupe_local(self.local_device, devices)
        self.state.set_devices(devices)
        for device in devices:
            self.storage.record_device(device)
        self.state.add_log(f"Scan complete: {len(devices)} device(s) found.")

    def start_pairing(self) -> None:
        if self.state.session:
            self.state.add_log("Disconnect before starting a new pairing session.")
            return
        if self.pending_pairing:
            self.state.add_log("Pairing session already active.")
            return
        pairing = self.pairing.create_pairing(self.local_device)
        self.pending_pairing = pairing
        self.state.set_pairing_code(pairing.code)
        self.state.add_log("Pairing session created. Awaiting peer request.")

    def link_to_device(self, device: Device) -> None:
        mode, conflict_rule = self._get_device_sync_preset(device.id)
        pairing = self.pairing.create_pairing(self.local_device)
        self.pending_pairing = None
        self.state.set_pairing_code(pairing.code)
        session = self.pairing.confirm_pairing(
            pairing,
            pairing.code,
            device,
            mode=mode,
            conflict_rule=conflict_rule,
        )
        self.state.set_session(session)
        self.state.set_transfers([])
        self.storage.record_device(device)
        self.storage.record_session(session)
        self.storage.record_audit_event(session.id, "session_linked", f"Linked to {device.name}.")
        self.state.set_requests(self.requests.list_requests(session.id))
        self.state.add_log(f"Linked to {device.name} with code {pairing.code}.")
        self.state.add_log(f"Session token issued: {session.token[:8]}...")
        self._broadcast_session_update(
            session.status,
            session.policy.mode,
            session.policy.approval_required,
            session.policy.conflict_rule,
        )

    def disconnect(self) -> None:
        if self.state.session:
            peer = self.state.session.peer_device.name
            session_id = self.state.session.id
            self.state.set_session(None)
            self.state.set_pairing_code("")
            self.state.set_transfers([])
            self.state.set_requests([])
            self.pending_pairing = None
            self.storage.update_session_status(session_id, "disconnected")
            self.storage.record_audit_event(session_id, "session_disconnected", f"Disconnected from {peer}.")
            self.state.add_log(f"Disconnected from {peer}.")
            self._broadcast_session_update("disconnected", "", False, "keep_both")

    def simulate_transfer(self) -> None:
        if not self.state.session:
            self.state.add_log("Link a device before starting a transfer.")
            return
        source_path = self.hyperbox.ensure_demo_file()
        dest_path = self.hyperbox.inbox / source_path.name
        self._start_transfer(
            source_path=source_path,
            dest_path=dest_path,
            direction="upload",
            request_id=None,
            network_transfer=False,
        )

    def simulate_request(self) -> None:
        if not self.state.session:
            self.state.add_log("Link a device before creating a request.")
            return
        sample_path = f"requests/sample_{uuid.uuid4().hex[:6]}.txt"
        request = self.requests.create_request(
            self.state.session.id,
            sample_path,
            requester="peer",
        )
        self.state.set_requests(self.requests.list_requests(self.state.session.id))
        self.state.add_log(f"Request queued: {request.path}")

    def approve_request(self, request_id: str) -> None:
        request = self._find_request(request_id)
        if not request:
            return
        updated = self.requests.update_status(request, "approved")
        self.state.set_requests(self.requests.list_requests(updated.session_id))
        self.state.add_log(f"Approved request: {updated.path}")

        source_path = self._resolve_request_source(updated)
        if not source_path:
            self.state.add_log("Unable to locate requested file for transfer.")
            return
        dest_path = self.hyperbox.inbox / source_path.name
        self._request_transfer_map[updated.id] = str(source_path)
        self._start_transfer(
            source_path=source_path,
            dest_path=dest_path,
            direction="upload",
            request_id=updated.id,
            network_transfer=updated.requester != "local",
        )

    def approve_request_with_source(self, request_id: str, source_path: str) -> None:
        request = self._find_request(request_id)
        if not request:
            return
        candidate = Path(source_path)
        if not candidate.exists():
            self.state.add_log("Selected source file does not exist.")
            return
        updated = self.requests.update_status(request, "approved")
        self.state.set_requests(self.requests.list_requests(updated.session_id))
        self.state.add_log(f"Approved request: {updated.path}")

        dest_path = self.hyperbox.inbox / candidate.name
        self._request_transfer_map[updated.id] = str(candidate)
        self._start_transfer(
            source_path=candidate,
            dest_path=dest_path,
            direction="upload",
            request_id=updated.id,
            network_transfer=updated.requester != "local",
        )

    def decline_request(self, request_id: str) -> None:
        request = self._find_request(request_id)
        if not request:
            return
        updated = self.requests.update_status(request, "declined")
        self.state.set_requests(self.requests.list_requests(updated.session_id))
        self.state.add_log(f"Declined request: {updated.path}")

    def get_request_history(self) -> list[FileRequest]:
        session_id = self.state.session.id if self.state.session else None
        return self.requests.list_requests_history(session_id)

    def get_request_history_all(self) -> list[FileRequest]:
        return self.requests.list_requests_history(None)

    def get_session_index(self) -> dict[str, str]:
        sessions = self.storage.list_sessions_with_peers()
        return {session["session_id"]: session["peer_name"] for session in sessions}

    def update_sync_rules(self, mode: str, conflict_rule: str) -> None:
        if not self.state.session:
            self.state.add_log("No active session to update sync rules.")
            return
        approval_required = mode == "approval"
        updated = self.pairing.update_session(
            self.state.session,
            self.state.session.status,
            mode,
            approval_required,
            conflict_rule,
        )
        self.state.set_session(updated)
        self.storage.record_session(updated)
        self._save_device_sync_preset(updated.peer_device.id, mode, conflict_rule)
        self.state.add_log(
            f"Sync rules updated: mode={mode}, conflict={conflict_rule}."
        )
        self._broadcast_session_update(
            updated.status,
            updated.policy.mode,
            updated.policy.approval_required,
            updated.policy.conflict_rule,
        )

    def _resolve_request_source(self, request: FileRequest) -> Path | None:
        requested_path = Path(request.path)
        if requested_path.is_absolute() and requested_path.exists():
            return requested_path
        candidate = self.hyperbox.root / requested_path
        if candidate.exists():
            return candidate
        demo = self.hyperbox.ensure_demo_file()
        self.state.add_log(f"Using demo file for request: {request.path}")
        return demo

    def start_control_server(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        if self._control_thread:
            return
        self.state.add_log(f"Starting control server on {host}:{port}...")

        def runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._control_loop = loop
            self.control_server = ControlServer(host, port, self._handle_control_message)
            loop.run_until_complete(self.control_server.start())
            self.state.add_log(f"Control server listening on {host}:{port}.")
            loop.run_forever()

        self._control_thread = threading.Thread(target=runner, daemon=True)
        self._control_thread.start()

    def shutdown(self) -> None:
        self._closing = True
        try:
            self.watcher.stop()
        except Exception:
            pass
        if self.mdns_service:
            try:
                self.mdns_service.stop()
            except Exception:
                pass
        if self._control_loop and self.control_server:
            try:
                asyncio.run_coroutine_threadsafe(self.control_server.stop(), self._control_loop)
                self._control_loop.call_soon_threadsafe(self._control_loop.stop)
            except Exception:
                pass
        self.storage.close()

    async def _handle_control_message(self, message: dict) -> None:
        message_type = message.get("type")
        payload = message.get("payload", {})
        self.state.add_log(f"Control message received: {message_type}")

        if message_type == "PAIRING_REQUEST":
            code = payload.get("pair_code")
            device_id = payload.get("device_id")
            if not code or not device_id:
                self.state.add_log("Pairing request missing code or device id.")
                return
            pairing = self.pending_pairing or self.pairing.find_by_code(code)
            if not pairing:
                self.state.add_log("No active pairing session found for code.")
                return
            peer_device = self._build_peer_device(payload)
            mode, conflict_rule = self._get_device_sync_preset(peer_device.id)
            session = self.pairing.confirm_pairing(
                pairing,
                code,
                peer_device,
                mode=mode,
                conflict_rule=conflict_rule,
            )
            self.pending_pairing = None
            self.state.set_session(session)
            self.state.set_pairing_code("")
            self.state.set_transfers([])
            self.storage.record_device(peer_device)
            self.storage.record_session(session)
            self.storage.record_audit_event(
                session.id, "session_linked", f"Linked to {peer_device.name}."
            )
            self.state.set_requests(self.requests.list_requests(session.id))
            self.state.add_log(f"Peer linked: {peer_device.name}.")
            self._broadcast_pairing_accept(session)
            self._broadcast_session_update(
                session.status,
                session.policy.mode,
                session.policy.approval_required,
                session.policy.conflict_rule,
            )
        elif message_type == "SESSION_UPDATE" and self.state.session:
            status = payload.get("status", self.state.session.status)
            mode = payload.get("mode", self.state.session.policy.mode)
            approval_required = payload.get(
                "approval_required", self.state.session.policy.approval_required
            )
            conflict_rule = payload.get(
                "conflict_rule", self.state.session.policy.conflict_rule
            )
            updated = self.pairing.update_session(
                self.state.session,
                status,
                mode,
                approval_required,
                conflict_rule,
            )
            self.state.set_session(updated)
            self.storage.record_session(updated)
        elif message_type == "TRANSFER_STATUS":
            job_id = payload.get("job_id")
            if not job_id:
                return
            job = TransferJob(
                id=job_id,
                path=payload.get("path", ""),
                direction=payload.get("direction", "download"),
                status=payload.get("status", "unknown"),
                size=int(payload.get("size", 0)),
                bytes_copied=int(payload.get("bytes_copied", 0)),
                progress=float(payload.get("progress", 0.0)),
                checksum=payload.get("checksum"),
                rate_mbps=float(payload.get("rate_mbps", 0.0)),
            )
            self.state.update_transfer(job)
            if self.state.session:
                self.storage.record_transfer(self.state.session.id, job)
        elif message_type == "TRANSFER_REQUEST" and self.state.session:
            path = payload.get("path", "")
            requester = payload.get("requester", "peer")
            request = self.requests.create_request(self.state.session.id, path, requester)
            self.state.set_requests(self.requests.list_requests(self.state.session.id))
            self.state.add_log(f"Transfer requested: {request.path}")

    def _handle_hyperbox_event(self, event_type: str, path: Path) -> None:
        if not self.state.session:
            return
        try:
            relative = path.relative_to(self.hyperbox.root)
        except ValueError:
            return
        mode = self.state.session.policy.mode
        now = time.monotonic()
        last_run = self._last_transfer_by_path.get(str(path), 0)
        if now - last_run < 1.0:
            return

        if self.hyperbox.requests in path.parents:
            if mode == "approval":
                request = self.requests.create_request(
                    self.state.session.id,
                    str(relative),
                    requester="local",
                )
                self.state.set_requests(self.requests.list_requests(self.state.session.id))
                self.state.add_log(f"Request file detected: {request.path}")
            else:
                self.state.add_log(f"Request ignored (mode={mode}): {relative}")
            return

        if self.hyperbox.outbox in path.parents:
            if mode in ("mirror", "copy") and event_type in ("created", "modified"):
                self._last_transfer_by_path[str(path)] = now
                self.state.add_log(f"Auto-sync outbox file: {relative}")
                self._start_transfer(
                    source_path=path,
                    dest_path=self.hyperbox.inbox / path.name,
                    direction="upload",
                    request_id=None,
                    network_transfer=False,
                )
            else:
                self.state.add_log(f"Outbox file detected: {relative}")
            return

        if self.hyperbox.inbox in path.parents:
            if mode == "mirror" and event_type in ("created", "modified"):
                self.state.add_log(f"Inbox updated (mirror sync): {relative}")
            else:
                self.state.add_log(f"Inbox file received: {relative}")

    def _start_transfer(
        self,
        source_path: Path,
        dest_path: Path,
        direction: str,
        request_id: Optional[str],
        network_transfer: bool,
    ) -> None:
        if not self.state.session:
            return
        if request_id:
            self._set_request_status(request_id, "in_progress")
        if not network_transfer:
            dest_path = self._apply_conflict_rule(dest_path)
            if dest_path is None:
                self.state.add_log("Transfer skipped due to conflict policy.")
                if request_id:
                    self._finalize_request(request_id, "skipped")
                return
        settings = self.get_transfer_settings()
        job = TransferJob(
            id=str(uuid.uuid4()),
            path=str(source_path),
            direction=direction,
            status="transferring",
            size=source_path.stat().st_size if source_path.exists() else 0,
        )
        self.state.update_transfer(job)
        self.storage.record_transfer(self.state.session.id, job)
        worker = threading.Thread(
            target=self._run_transfer_job,
            args=(
                self.state.session.id,
                job,
                source_path,
                dest_path,
                settings["chunk_size_mb"],
                settings["max_bandwidth"],
                settings["retry_policy"],
                settings["max_retries"],
                request_id,
                network_transfer,
            ),
            daemon=True,
        )
        worker.start()

    def _run_transfer_job(
        self,
        session_id: str,
        job: TransferJob,
        source_path: Path,
        dest_path: Path,
        chunk_size_mb: int,
        max_bandwidth: str,
        retry_policy: str,
        max_retries: int,
        request_id: Optional[str],
        network_transfer: bool,
    ) -> None:
        def on_progress(bytes_copied: int, total_size: int) -> None:
            progress = bytes_copied / total_size if total_size else 1.0
            now = time.monotonic()
            last_bytes, last_time = self._transfer_metrics.get(job.id, (0, now))
            delta_bytes = bytes_copied - last_bytes
            delta_time = max(now - last_time, 0.0001)
            rate_mbps = (delta_bytes / delta_time) / (1024 * 1024)
            self._transfer_metrics[job.id] = (bytes_copied, now)
            updated = TransferJob(
                id=job.id,
                path=job.path,
                direction=job.direction,
                status="transferring",
                size=total_size,
                bytes_copied=bytes_copied,
                progress=progress,
                checksum=job.checksum,
                rate_mbps=rate_mbps,
            )
            self.state.update_transfer(updated)
            if not self._closing:
                try:
                    self.storage.record_transfer(session_id, updated)
                except Exception:
                    pass

        try:
            if network_transfer:
                result = self._send_over_network(
                    source_path,
                    chunk_size_mb,
                    max_bandwidth,
                    on_progress,
                    job,
                )
            else:
                result = self.transfer.copy_with_checksum(
                    str(source_path),
                    str(dest_path),
                    chunk_size=chunk_size_mb * 1024 * 1024,
                    on_progress=on_progress,
                    resume=True,
                    max_bandwidth=self._parse_bandwidth(max_bandwidth),
                    retry_policy=retry_policy,
                    max_retries=max_retries,
                )
            finished = TransferJob(
                id=job.id,
                path=job.path,
                direction=job.direction,
                status="complete",
                size=job.size,
                bytes_copied=result.bytes_copied,
                progress=1.0,
                checksum=result.checksum,
                rate_mbps=0.0,
            )
            self.state.update_transfer(finished)
            if not self._closing:
                try:
                    self.storage.record_transfer(session_id, finished)
                except Exception:
                    pass
            self._broadcast_transfer_status(finished)
            if request_id:
                self._finalize_request(request_id, "completed")
        except Exception as exc:
            failed = TransferJob(
                id=job.id,
                path=job.path,
                direction=job.direction,
                status="failed",
                size=job.size,
                bytes_copied=job.bytes_copied,
                progress=job.progress,
                checksum=job.checksum,
                rate_mbps=0.0,
            )
            self.state.update_transfer(failed)
            if not self._closing:
                try:
                    self.storage.record_transfer(session_id, failed)
                except Exception:
                    pass
            self.state.add_log(f"Transfer failed: {exc}")
            self._broadcast_transfer_status(failed)
            if request_id:
                self._finalize_request(request_id, "failed")

    def _broadcast_session_update(
        self,
        status: str,
        mode: str,
        approval_required: bool,
        conflict_rule: str,
    ) -> None:
        if not self.control_server or not self._control_loop or not self.state.session:
            return
        payload = {
            "session_id": self.state.session.id,
            "status": status,
            "mode": mode,
            "approval_required": approval_required,
            "conflict_rule": conflict_rule,
        }
        message = encode_message("SESSION_UPDATE", payload)
        asyncio.run_coroutine_threadsafe(
            self.control_server.broadcast(message), self._control_loop
        )

    def _broadcast_pairing_accept(self, session) -> None:
        if not self.control_server or not self._control_loop:
            return
        payload = {
            "session_id": session.id,
            "device_id": self.local_device.id,
            "session_token": session.token,
        }
        message = encode_message("PAIRING_ACCEPT", payload)
        asyncio.run_coroutine_threadsafe(
            self.control_server.broadcast(message), self._control_loop
        )

    def _broadcast_transfer_status(self, job: TransferJob) -> None:
        if not self.control_server or not self._control_loop or not self.state.session:
            return
        payload = {
            "job_id": job.id,
            "status": job.status,
            "progress": job.progress,
            "checksum": job.checksum,
        }
        message = encode_message("TRANSFER_STATUS", payload)
        asyncio.run_coroutine_threadsafe(
            self.control_server.broadcast(message), self._control_loop
        )

    def _broadcast_transfer_offer(
        self,
        job_id: str,
        filename: str,
        size: int,
        host: str,
        port: int,
    ) -> None:
        if not self.control_server or not self._control_loop or not self.state.session:
            return
        payload = {
            "session_id": self.state.session.id,
            "job_id": job_id,
            "filename": filename,
            "size": size,
            "host": host,
            "port": port,
            "conflict_rule": self.state.session.policy.conflict_rule,
        }
        message = encode_message("TRANSFER_OFFER", payload)
        asyncio.run_coroutine_threadsafe(
            self.control_server.broadcast(message), self._control_loop
        )

    def _send_over_network(
        self,
        source_path: Path,
        chunk_size_mb: int,
        max_bandwidth: str,
        on_progress,
        job: TransferJob,
    ):
        sender = FileSender(
            host="0.0.0.0",
            port=0,
            chunk_size=chunk_size_mb * 1024 * 1024,
        )
        port = sender.open()
        host_ip = self.local_device.ip or "127.0.0.1"
        size = source_path.stat().st_size if source_path.exists() else 0
        self._broadcast_transfer_offer(job.id, source_path.name, size, host_ip, port)
        result = sender.send_file(
            source_path,
            on_progress=on_progress,
            max_bandwidth=self._parse_bandwidth(max_bandwidth),
        )
        sender.close()
        return result

    def _find_request(self, request_id: str) -> FileRequest | None:
        for request in self.state.requests:
            if request.id == request_id:
                return request
        return None

    def _set_request_status(self, request_id: str, status: str) -> None:
        request = self._find_request(request_id)
        if not request:
            return
        updated = self.requests.update_status(request, status)
        self.state.set_requests(self.requests.list_requests(updated.session_id))

    def _finalize_request(self, request_id: str, status: str) -> None:
        self._set_request_status(request_id, status)

    def _parse_bandwidth(self, value: str) -> int | None:
        if not value or value == "unlimited":
            return None
        cleaned = value.replace(" ", "")
        if cleaned.endswith("MB/s"):
            return int(float(cleaned.replace("MB/s", "")) * 1024 * 1024)
        if cleaned.endswith("KB/s"):
            return int(float(cleaned.replace("KB/s", "")) * 1024)
        if cleaned.endswith("GB/s"):
            return int(float(cleaned.replace("GB/s", "")) * 1024 * 1024 * 1024)
        return None

    def _get_device_sync_preset(self, device_id: str) -> tuple[str, str]:
        mode = self.storage.get_preference(
            f"device.{device_id}.sync_mode", "approval"
        )
        conflict_rule = self.storage.get_preference(
            f"device.{device_id}.conflict_rule", "keep_both"
        )
        return mode, conflict_rule

    def _save_device_sync_preset(self, device_id: str, mode: str, conflict_rule: str) -> None:
        self.storage.set_preference(f"device.{device_id}.sync_mode", mode)
        self.storage.set_preference(f"device.{device_id}.conflict_rule", conflict_rule)

    def _build_peer_device(self, payload: dict) -> Device:
        device_id = payload.get("device_id", str(uuid.uuid4()))
        name = payload.get("device_name", "Peer")
        ip = payload.get("device_ip", "0.0.0.0")
        capabilities = payload.get("capabilities", [])
        if isinstance(capabilities, str):
            capabilities = [c for c in capabilities.split(",") if c]
        return Device(
            id=device_id,
            name=name,
            ip=ip,
            status="online",
            capabilities=capabilities,
        )

    def _apply_conflict_rule(self, dest_path: Path) -> Path | None:
        if not self.state.session:
            return dest_path
        if self.state.session.policy.mode != "mirror":
            return dest_path
        if not dest_path.exists():
            return dest_path

        rule = self.state.session.policy.conflict_rule
        if rule == "prefer_host":
            return dest_path
        if rule == "prefer_peer":
            return None
        if rule == "keep_both":
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            suffix = dest_path.suffix
            base = dest_path.stem
            return dest_path.with_name(f"{base}_conflict_{timestamp}{suffix}")
        return dest_path

    def get_transfer_settings(self) -> dict:
        settings = dict(self._transfer_defaults)
        settings["chunk_size_mb"] = int(
            self.storage.get_preference(
                "transfer.chunk_size_mb", str(settings["chunk_size_mb"])
            )
        )
        settings["max_bandwidth"] = self.storage.get_preference(
            "transfer.max_bandwidth", settings["max_bandwidth"]
        )
        settings["retry_policy"] = self.storage.get_preference(
            "transfer.retry_policy", settings["retry_policy"]
        )
        settings["max_retries"] = int(
            self.storage.get_preference(
                "transfer.max_retries", str(settings["max_retries"])
            )
        )
        settings["encryption"] = self.storage.get_preference(
            "transfer.encryption", str(settings["encryption"])
        ) in ("True", "true", "1")
        return settings

    def get_transfer_limit_mbps(self) -> float | None:
        settings = self.get_transfer_settings()
        limit_bytes = self._parse_bandwidth(settings["max_bandwidth"])
        if not limit_bytes:
            return None
        return limit_bytes / (1024 * 1024)

    def save_transfer_settings(self, settings: dict) -> None:
        self.storage.set_preference(
            "transfer.chunk_size_mb", str(settings["chunk_size_mb"])
        )
        self.storage.set_preference(
            "transfer.max_bandwidth", str(settings["max_bandwidth"])
        )
        self.storage.set_preference(
            "transfer.retry_policy", str(settings["retry_policy"])
        )
        self.storage.set_preference(
            "transfer.max_retries", str(settings["max_retries"])
        )
        self.storage.set_preference(
            "transfer.encryption", str(settings["encryption"])
        )
        self.state.add_log("Transfer settings updated.")


def _build_local_device() -> Device:
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        local_ip = "127.0.0.1"
    return Device(
        id=str(uuid.uuid4()),
        name=hostname,
        ip=local_ip,
        status="local",
        capabilities=["hyperbox", "requests"],
    )


def _dedupe_local(local_device: Device, devices: list[Device]) -> list[Device]:
    deduped = [local_device]
    for device in devices:
        if device.name == local_device.name and device.ip == local_device.ip:
            continue
        deduped.append(device)
    return deduped

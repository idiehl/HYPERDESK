from __future__ import annotations

import hashlib
import os
import socket
import struct
import time
from pathlib import Path
from typing import Optional

from dataclasses import dataclass

from hyperdesk.transfer.engine import TransferResult


class FileSender:
    def __init__(self, host: str = "0.0.0.0", port: int = 0, chunk_size: int = 1024 * 1024) -> None:
        self.host = host
        self.port = port
        self.chunk_size = chunk_size
        self._server: Optional[socket.socket] = None

    def open(self) -> int:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(1)
        self.port = server.getsockname()[1]
        self._server = server
        return self.port

    def send_file(
        self,
        source_path: Path,
        on_progress=None,
        max_bandwidth: Optional[int] = None,
    ) -> TransferResult:
        if not self._server:
            raise RuntimeError("FileSender not opened.")

        hasher = hashlib.sha256()
        total_size = source_path.stat().st_size
        start_time = time.monotonic()
        bytes_sent = 0

        conn, _addr = self._server.accept()
        with conn, open(source_path, "rb") as handle:
            name_bytes = source_path.name.encode("utf-8")
            header = struct.pack("!I", len(name_bytes)) + name_bytes
            header += struct.pack("!Q", total_size)
            conn.sendall(header)

            while True:
                chunk = handle.read(self.chunk_size)
                if not chunk:
                    break
                conn.sendall(chunk)
                hasher.update(chunk)
                bytes_sent += len(chunk)
                if on_progress:
                    on_progress(bytes_sent, total_size)
                _apply_rate_limit(bytes_sent, start_time, max_bandwidth)

        return TransferResult(bytes_copied=bytes_sent, checksum=hasher.hexdigest())

    def close(self) -> None:
        if self._server:
            self._server.close()
            self._server = None


@dataclass(frozen=True)
class ReceiveResult:
    path: Path
    bytes_received: int
    checksum: str
    skipped: bool


def receive_file(
    host: str,
    port: int,
    dest_dir: Path,
    on_progress=None,
    conflict_rule: str = "keep_both",
) -> ReceiveResult:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with socket.create_connection((host, port)) as conn:
        header = _recv_exact(conn, 4)
        (name_len,) = struct.unpack("!I", header)
        name_bytes = _recv_exact(conn, name_len)
        (size,) = struct.unpack("!Q", _recv_exact(conn, 8))
        filename = name_bytes.decode("utf-8")
        dest_path = _resolve_conflict_dest(dest_dir / filename, conflict_rule)
        discard = False
        if dest_path is None:
            dest_path = dest_dir / f".incoming_{filename}"
            discard = True
        remaining = size
        hasher = hashlib.sha256()
        bytes_received = 0
        with open(dest_path, "wb") as out:
            while remaining > 0:
                chunk = conn.recv(min(1024 * 1024, remaining))
                if not chunk:
                    break
                out.write(chunk)
                hasher.update(chunk)
                bytes_received += len(chunk)
                remaining -= len(chunk)
                if on_progress:
                    on_progress(bytes_received, size)

    if discard:
        dest_path.unlink(missing_ok=True)
        return ReceiveResult(dest_path, bytes_received, "", True)
    return ReceiveResult(dest_path, bytes_received, hasher.hexdigest(), False)


def _recv_exact(conn: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            raise ConnectionError("Unexpected end of stream")
        data += chunk
    return data


def _apply_rate_limit(bytes_copied: int, start_time: float, max_bandwidth: Optional[int]) -> None:
    if not max_bandwidth:
        return
    elapsed = time.monotonic() - start_time
    if elapsed <= 0:
        return
    expected_time = bytes_copied / max_bandwidth
    if expected_time > elapsed:
        time.sleep(expected_time - elapsed)


def _resolve_conflict_dest(dest_path: Path, conflict_rule: str) -> Path | None:
    if not dest_path.exists():
        return dest_path
    if conflict_rule == "prefer_host":
        return dest_path
    if conflict_rule == "prefer_peer":
        return None
    if conflict_rule == "keep_both":
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        suffix = dest_path.suffix
        base = dest_path.stem
        return dest_path.with_name(f"{base}_conflict_{timestamp}{suffix}")
    return dest_path

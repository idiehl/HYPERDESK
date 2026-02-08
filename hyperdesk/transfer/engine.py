from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Callable, Optional


ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class TransferResult:
    bytes_copied: int
    checksum: str


class TransferEngine:
    def copy_with_checksum(
        self,
        source_path: str,
        dest_path: str,
        chunk_size: int = 1024 * 1024,
        resume: bool = False,
        on_progress: Optional[ProgressCallback] = None,
        max_bandwidth: Optional[int] = None,
        retry_policy: str = "exponential",
        max_retries: int = 3,
    ) -> TransferResult:
        attempt = 0
        while True:
            try:
                return self._copy_once(
                    source_path,
                    dest_path,
                    chunk_size=chunk_size,
                    resume=resume,
                    on_progress=on_progress,
                    max_bandwidth=max_bandwidth,
                )
            except Exception:
                attempt += 1
                if retry_policy == "none" or attempt > max_retries:
                    raise
                delay = _retry_delay(attempt, retry_policy)
                time.sleep(delay)

    def _copy_once(
        self,
        source_path: str,
        dest_path: str,
        chunk_size: int,
        resume: bool,
        on_progress: Optional[ProgressCallback],
        max_bandwidth: Optional[int],
    ) -> TransferResult:
        total_size = os.path.getsize(source_path)
        offset = 0

        if resume and os.path.exists(dest_path):
            offset = os.path.getsize(dest_path)
            if offset > total_size:
                offset = 0

        mode = "ab" if resume and offset > 0 else "wb"
        bytes_copied = offset
        start_time = time.monotonic()

        with open(source_path, "rb") as source_file, open(dest_path, mode) as dest_file:
            if offset:
                source_file.seek(offset)
            while True:
                chunk = source_file.read(chunk_size)
                if not chunk:
                    break
                dest_file.write(chunk)
                bytes_copied += len(chunk)
                if on_progress:
                    on_progress(bytes_copied, total_size)
                _apply_rate_limit(bytes_copied, start_time, max_bandwidth)

        checksum = compute_sha256(dest_path, chunk_size=chunk_size)
        return TransferResult(bytes_copied=bytes_copied, checksum=checksum)


def compute_sha256(path: str, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _apply_rate_limit(bytes_copied: int, start_time: float, max_bandwidth: Optional[int]) -> None:
    if not max_bandwidth:
        return
    elapsed = time.monotonic() - start_time
    if elapsed <= 0:
        return
    expected_time = bytes_copied / max_bandwidth
    if expected_time > elapsed:
        time.sleep(expected_time - elapsed)


def _retry_delay(attempt: int, policy: str) -> float:
    if policy == "linear":
        return min(1.0 * attempt, 10.0)
    return min(0.5 * (2**attempt), 10.0)

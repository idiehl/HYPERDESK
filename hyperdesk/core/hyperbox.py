from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


class HyperboxManager:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or (Path.cwd() / "hyperbox")
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.requests = self.root / "requests"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.outbox.mkdir(parents=True, exist_ok=True)
        self.requests.mkdir(parents=True, exist_ok=True)

    def ensure_demo_file(self, size_bytes: int = 2 * 1024 * 1024) -> Path:
        demo_path = self.root / "demo_payload.bin"
        if demo_path.exists() and demo_path.stat().st_size == size_bytes:
            return demo_path
        demo_path.write_bytes(os.urandom(size_bytes))
        return demo_path

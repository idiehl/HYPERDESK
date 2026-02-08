from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


EventCallback = Callable[[str, Path], None]


class HyperboxWatcher:
    def __init__(self, root: Path, on_event: EventCallback) -> None:
        self.root = root
        self.on_event = on_event
        self._observer: Optional[Observer] = None

    def start(self) -> None:
        if self._observer:
            return
        handler = _HyperboxEventHandler(self.on_event)
        observer = Observer()
        observer.schedule(handler, str(self.root), recursive=True)
        observer.daemon = True
        observer.start()
        self._observer = observer

    def stop(self) -> None:
        if not self._observer:
            return
        self._observer.stop()
        self._observer.join(timeout=2)
        self._observer = None


class _HyperboxEventHandler(FileSystemEventHandler):
    def __init__(self, on_event: EventCallback) -> None:
        super().__init__()
        self.on_event = on_event

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        self.on_event("created", Path(event.src_path))

    def on_modified(self, event) -> None:
        if event.is_directory:
            return
        self.on_event("modified", Path(event.src_path))

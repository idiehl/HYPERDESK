from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from hyperdesk.core.models import FileRequest
from hyperdesk.core.storage import Storage


class RequestQueue:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def create_request(self, session_id: str, path: str, requester: str) -> FileRequest:
        request = FileRequest(
            id=str(uuid.uuid4()),
            session_id=session_id,
            path=path,
            requester=requester,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        self.storage.record_request(request)
        return request

    def update_status(self, request: FileRequest, status: str) -> FileRequest:
        updated = FileRequest(
            id=request.id,
            session_id=request.session_id,
            path=request.path,
            requester=request.requester,
            status=status,
            created_at=request.created_at,
        )
        self.storage.record_request(updated)
        return updated

    def list_requests(self, session_id: str) -> List[FileRequest]:
        return self.storage.list_requests(session_id)

    def list_requests_history(self, session_id: str | None = None) -> List[FileRequest]:
        return self.storage.list_requests_history(session_id)

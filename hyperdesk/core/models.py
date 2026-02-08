from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class Device:
    id: str
    name: str
    ip: str
    status: str = "online"
    capabilities: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class PermissionPolicy:
    mode: str
    approval_required: bool
    conflict_rule: str = "keep_both"


@dataclass(frozen=True)
class Session:
    id: str
    host_device: Device
    peer_device: Device
    status: str
    policy: PermissionPolicy
    token: str
    created_at: datetime


@dataclass(frozen=True)
class PairingSession:
    id: str
    code: str
    host_device: Device
    created_at: datetime


@dataclass
class TransferJob:
    id: str
    path: str
    direction: str
    status: str
    size: int = 0
    bytes_copied: int = 0
    progress: float = 0.0
    checksum: Optional[str] = None
    rate_mbps: float = 0.0


@dataclass(frozen=True)
class FileRequest:
    id: str
    session_id: str
    path: str
    requester: str
    status: str
    created_at: datetime

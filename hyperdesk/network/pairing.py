from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Dict

from hyperdesk.core.models import Device, PairingSession, PermissionPolicy, Session


class PairingManager:
    def __init__(self) -> None:
        self._active: Dict[str, PairingSession] = {}
        self._active_by_code: Dict[str, PairingSession] = {}

    def create_pairing(self, host_device: Device) -> PairingSession:
        code = f"{secrets.randbelow(1_000_000):06d}"
        pairing = PairingSession(
            id=str(uuid.uuid4()),
            code=code,
            host_device=host_device,
            created_at=datetime.now(timezone.utc),
        )
        self._active[pairing.id] = pairing
        self._active_by_code[pairing.code] = pairing
        return pairing

    def accept_pairing(
        self,
        pairing: PairingSession,
        peer_device: Device,
        mode: str = "approval",
    ) -> Session:
        return self.confirm_pairing(
            pairing, pairing.code, peer_device, mode=mode, conflict_rule="keep_both"
        )

    def confirm_pairing(
        self,
        pairing: PairingSession,
        code: str,
        peer_device: Device,
        mode: str = "approval",
        conflict_rule: str = "keep_both",
        allow_browse: bool = True,
        allow_requests: bool = True,
        allow_edits: bool = False,
        edit_mode: str = "copy_on_edit",
        allow_client_share: bool = True,
        session_id: str | None = None,
        token: str | None = None,
    ) -> Session:
        if pairing.code != code:
            raise ValueError("Invalid pairing code.")
        session = self._create_session(
            pairing.host_device,
            peer_device,
            mode=mode,
            conflict_rule=conflict_rule,
            allow_browse=allow_browse,
            allow_requests=allow_requests,
            allow_edits=allow_edits,
            edit_mode=edit_mode,
            allow_client_share=allow_client_share,
            session_id=session_id,
            token=token,
        )
        self._active.pop(pairing.id, None)
        self._active_by_code.pop(pairing.code, None)
        return session

    def find_by_code(self, code: str) -> PairingSession | None:
        return self._active_by_code.get(code)

    def update_session(
        self,
        session: Session,
        status: str,
        mode: str,
        approval_required: bool,
        conflict_rule: str,
        allow_browse: bool,
        allow_requests: bool,
        allow_edits: bool,
        edit_mode: str,
        allow_client_share: bool,
    ) -> Session:
        policy = PermissionPolicy(
            mode=mode,
            approval_required=approval_required,
            conflict_rule=conflict_rule,
            allow_browse=allow_browse,
            allow_requests=allow_requests,
            allow_edits=allow_edits,
            edit_mode=edit_mode,
            allow_client_share=allow_client_share,
        )
        return Session(
            id=session.id,
            host_device=session.host_device,
            peer_device=session.peer_device,
            status=status,
            policy=policy,
            token=session.token,
            created_at=session.created_at,
        )

    def _create_session(
        self,
        host_device: Device,
        peer_device: Device,
        mode: str,
        conflict_rule: str,
        allow_browse: bool,
        allow_requests: bool,
        allow_edits: bool,
        edit_mode: str,
        allow_client_share: bool,
        session_id: str | None = None,
        token: str | None = None,
    ) -> Session:
        policy = PermissionPolicy(
            mode=mode,
            approval_required=(mode == "approval"),
            conflict_rule=conflict_rule,
            allow_browse=allow_browse,
            allow_requests=allow_requests,
            allow_edits=allow_edits,
            edit_mode=edit_mode,
            allow_client_share=allow_client_share,
        )
        return Session(
            id=session_id or str(uuid.uuid4()),
            host_device=host_device,
            peer_device=peer_device,
            status="connected",
            policy=policy,
            token=token or secrets.token_urlsafe(16),
            created_at=datetime.now(timezone.utc),
        )

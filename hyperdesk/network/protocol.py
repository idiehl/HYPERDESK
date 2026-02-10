from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional


PROTOCOL_VERSION = "0.1"

MESSAGE_SCHEMAS: Dict[str, Iterable[str]] = {
    "DISCOVERY_PING": ("device_id", "name", "capabilities"),
    "DISCOVERY_OFFER": ("device_id", "name", "ip", "capabilities"),
    "PAIRING_REQUEST": ("device_id", "pair_code"),
    "PAIRING_ACCEPT": ("session_id", "device_id", "session_token"),
    "PAIRING_OFFER": (
        "session_id",
        "host_id",
        "host_name",
        "host_ip",
        "mode",
        "approval_required",
        "conflict_rule",
        "allow_browse",
        "allow_requests",
        "allow_edits",
        "edit_mode",
        "allow_client_share",
    ),
    "PAIRING_CONFIRM": ("session_id", "device_id"),
    "PAIRING_DECLINE": ("session_id", "device_id"),
    "SESSION_UPDATE": (
        "session_id",
        "status",
        "mode",
        "approval_required",
        "conflict_rule",
        "allow_browse",
        "allow_requests",
        "allow_edits",
        "edit_mode",
        "allow_client_share",
    ),
    "TRANSFER_REQUEST": ("session_id", "path", "direction", "size"),
    "TRANSFER_STATUS": ("job_id", "status", "progress", "checksum"),
    "TRANSFER_OFFER": ("session_id", "job_id", "filename", "size", "host", "port"),
}


class ProtocolError(ValueError):
    pass


def encode_message(
    message_type: str,
    payload: Dict[str, Any],
    request_id: Optional[str] = None,
) -> str:
    if message_type not in MESSAGE_SCHEMAS:
        raise ProtocolError(f"Unknown message type: {message_type}")
    _validate_payload(message_type, payload)
    message = {
        "version": PROTOCOL_VERSION,
        "type": message_type,
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    return json.dumps(message)


def decode_message(raw_message: str) -> Dict[str, Any]:
    try:
        data = json.loads(raw_message)
    except json.JSONDecodeError as exc:
        raise ProtocolError("Invalid JSON payload") from exc

    for key in ("version", "type", "timestamp", "payload"):
        if key not in data:
            raise ProtocolError(f"Missing required field: {key}")

    message_type = data["type"]
    payload = data["payload"]
    if message_type not in MESSAGE_SCHEMAS:
        raise ProtocolError(f"Unknown message type: {message_type}")
    if not isinstance(payload, dict):
        raise ProtocolError("Payload must be an object")
    _validate_payload(message_type, payload)
    return data


def _validate_payload(message_type: str, payload: Dict[str, Any]) -> None:
    required = MESSAGE_SCHEMAS.get(message_type, ())
    missing = [key for key in required if key not in payload]
    if missing:
        raise ProtocolError(
            f"Payload missing fields for {message_type}: {', '.join(missing)}"
        )

from __future__ import annotations

import argparse
import asyncio
import socket
import time
import uuid
from pathlib import Path

from hyperdesk.network.control import ControlClient
from hyperdesk.transfer.channel import receive_file


async def run_peer(
    host: str,
    port: int,
    pair_code: str,
    request_path: str | None,
    inbox_dir: Path,
) -> None:
    client = ControlClient(f"ws://{host}:{port}")
    await client.connect()

    device_id = str(uuid.uuid4())
    device_name = socket.gethostname()
    device_ip = _get_local_ip()
    await client.send(
        "PAIRING_REQUEST",
        {
            "device_id": device_id,
            "pair_code": pair_code,
            "device_name": device_name,
            "device_ip": device_ip,
            "capabilities": ["hyperbox", "requests"],
        },
    )

    session_id = None
    session_token = None
    print(f"[peer] Pairing request sent from {device_name}.")

    while True:
        message = await client.recv()
        message_type = message.get("type")
        payload = message.get("payload", {})
        print(f"[peer] Received: {message_type}")
        if message_type == "PAIRING_ACCEPT":
            session_id = payload.get("session_id")
            session_token = payload.get("session_token")
            print(f"[peer] Session active: {session_id} token={session_token[:8]}...")
            if request_path:
                await client.send(
                    "TRANSFER_REQUEST",
                    {
                        "session_id": session_id,
                        "path": request_path,
                        "direction": "download",
                        "size": 0,
                        "requester": device_name,
                    },
                )
                print(f"[peer] Requested file: {request_path}")
        elif message_type == "SESSION_UPDATE":
            status = payload.get("status")
            print(f"[peer] Session status: {status}")
        elif message_type == "TRANSFER_OFFER":
            offer_host = payload.get("host", host)
            offer_port = int(payload.get("port", port))
            filename = payload.get("filename", "file.bin")
            job_id = payload.get("job_id")
            conflict_rule = payload.get("conflict_rule", "keep_both")
            print(f"[peer] Receiving file: {filename} from {offer_host}:{offer_port}")

            loop = asyncio.get_running_loop()
            last_bytes = 0
            last_time = time.monotonic()

            def on_progress(bytes_received: int, total_size: int) -> None:
                nonlocal last_bytes, last_time
                now = time.monotonic()
                delta_bytes = bytes_received - last_bytes
                delta_time = max(now - last_time, 0.0001)
                rate_mbps = (delta_bytes / delta_time) / (1024 * 1024)
                last_bytes = bytes_received
                last_time = now
                if job_id:
                    asyncio.run_coroutine_threadsafe(
                        client.send(
                            "TRANSFER_STATUS",
                            {
                                "job_id": job_id,
                                "path": filename,
                                "status": "receiving",
                                "progress": bytes_received / total_size if total_size else 1.0,
                                "checksum": "",
                                "bytes_copied": bytes_received,
                                "size": total_size,
                                "direction": "download",
                                "rate_mbps": rate_mbps,
                            },
                        ),
                        loop,
                    )

            result = await asyncio.to_thread(
                receive_file,
                offer_host,
                offer_port,
                inbox_dir,
                on_progress,
                conflict_rule,
            )
            if result.skipped:
                status = "skipped"
                checksum = ""
            else:
                status = "complete"
                checksum = result.checksum
            if job_id:
                await client.send(
                    "TRANSFER_STATUS",
                    {
                        "job_id": job_id,
                        "path": filename,
                        "status": status,
                        "progress": 1.0,
                        "checksum": checksum,
                        "bytes_copied": result.bytes_received,
                        "size": result.bytes_received,
                        "direction": "download",
                        "rate_mbps": 0.0,
                    },
                )
            print(f"[peer] File saved to: {result.path}")
        elif message_type == "TRANSFER_STATUS":
            progress = payload.get("progress", 0.0)
            print(f"[peer] Transfer progress: {progress:.0%}")


def _get_local_ip() -> str:
    hostname = socket.gethostname()
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return "127.0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(description="HYPERDESK peer client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--pair-code", required=True)
    parser.add_argument("--request", dest="request_path")
    parser.add_argument("--inbox", dest="inbox_dir", default="peer_inbox")
    args = parser.parse_args()
    asyncio.run(
        run_peer(
            args.host,
            args.port,
            args.pair_code,
            args.request_path,
            Path(args.inbox_dir),
        )
    )


if __name__ == "__main__":
    main()

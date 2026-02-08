from __future__ import annotations

import os
import socket
import time
import uuid
from typing import List, Optional

from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf

from hyperdesk.core.models import Device


SERVICE_TYPE = "_hyperdesk._tcp.local."


class NetworkDiscovery:
    """Discovery service with optional mDNS support.

    Set HYPERDESK_USE_MDNS=1 to enable zeroconf.
    """

    def __init__(self, use_mdns: Optional[bool] = None) -> None:
        if use_mdns is None:
            use_mdns = os.getenv("HYPERDESK_USE_MDNS", "0") == "1"
        self.use_mdns = use_mdns

    def scan(self, limit: int = 6, timeout: float = 1.5) -> List[Device]:
        if self.use_mdns:
            try:
                devices = ZeroconfDiscovery().scan(timeout=timeout)
                if devices:
                    return devices[:limit]
            except Exception:
                pass
        return _simulate_devices(limit)


class ZeroconfDiscovery:
    def __init__(self) -> None:
        self._zeroconf = Zeroconf()

    def scan(self, timeout: float = 1.5) -> List[Device]:
        listener = _ZeroconfListener()
        browser = ServiceBrowser(self._zeroconf, SERVICE_TYPE, listener)
        time.sleep(timeout)
        browser.cancel()
        self._zeroconf.close()
        return listener.devices


class ZeroconfService:
    def __init__(self, device: Device, port: int = 8765) -> None:
        self.device = device
        self.port = port
        self._zeroconf = Zeroconf()
        self._info = _build_service_info(device, port)

    def start(self) -> None:
        self._zeroconf.register_service(self._info)

    def stop(self) -> None:
        self._zeroconf.unregister_service(self._info)
        self._zeroconf.close()


class _ZeroconfListener(ServiceListener):
    def __init__(self) -> None:
        self.devices: List[Device] = []

    def add_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        info = zeroconf.get_service_info(service_type, name)
        device = _device_from_info(info)
        if device:
            self.devices.append(device)

    def update_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        info = zeroconf.get_service_info(service_type, name)
        device = _device_from_info(info)
        if device:
            self.devices.append(device)

    def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        return None


def _get_local_identity() -> tuple[str, str]:
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        local_ip = "127.0.0.1"
    return hostname, local_ip


def _simulate_devices(limit: int) -> List[Device]:
    hostname, local_ip = _get_local_identity()
    devices = [
        Device(
            id=str(uuid.uuid4()),
            name=hostname,
            ip=local_ip,
            status="local",
            capabilities=["hyperbox", "requests"],
        )
    ]
    for index, name in enumerate(
        ("MYLAPTOP2", "ALIENWAREPC", "IPAD", "SAMSUNGFLIP3", "WORKSTATION")
    ):
        devices.append(
            Device(
                id=str(uuid.uuid4()),
                name=name,
                ip=f"192.168.1.{100 + index}",
                status="online",
                capabilities=["hyperbox"],
            )
        )
    return devices[:limit]


def _build_service_info(device: Device, port: int) -> ServiceInfo:
    properties = {
        b"device_id": device.id.encode(),
        b"name": device.name.encode(),
        b"capabilities": ",".join(device.capabilities).encode(),
    }
    addresses = [socket.inet_aton(device.ip)]
    service_name = f"{device.name}-{device.id}.{SERVICE_TYPE}"
    return ServiceInfo(
        SERVICE_TYPE,
        service_name,
        addresses=addresses,
        port=port,
        properties=properties,
        server=f"{device.name}.local.",
    )


def _device_from_info(info: Optional[ServiceInfo]) -> Optional[Device]:
    if not info:
        return None
    try:
        ip = socket.inet_ntoa(info.addresses[0]) if info.addresses else "0.0.0.0"
    except OSError:
        ip = "0.0.0.0"
    props = {k.decode(): v.decode() for k, v in (info.properties or {}).items()}
    name = props.get("name") or info.name.split(".")[0]
    device_id = props.get("device_id", str(uuid.uuid4()))
    capabilities = [c for c in props.get("capabilities", "").split(",") if c]
    return Device(
        id=device_id,
        name=name,
        ip=ip,
        status="online",
        capabilities=capabilities,
    )

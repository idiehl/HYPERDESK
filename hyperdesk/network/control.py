from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional, Set

import websockets

from hyperdesk.network.protocol import decode_message, encode_message


MessageHandler = Callable[[dict], Awaitable[None]]


class ControlServer:
    def __init__(self, host: str, port: int, on_message: MessageHandler) -> None:
        self.host = host
        self.port = port
        self.on_message = on_message
        self._server: Optional[asyncio.AbstractServer] = None
        self._connections: Set[websockets.WebSocketServerProtocol] = set()

    async def start(self) -> None:
        self._server = await websockets.serve(self._handler, self.host, self.port)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self._connections.clear()

    async def broadcast(self, message: str) -> None:
        if not self._connections:
            return
        disconnected = set()
        for socket in self._connections:
            try:
                await socket.send(message)
            except Exception:
                disconnected.add(socket)
        for socket in disconnected:
            self._connections.discard(socket)

    async def _handler(self, websocket) -> None:
        self._connections.add(websocket)
        try:
            async for raw_message in websocket:
                data = decode_message(raw_message)
                await self.on_message(data)
                await asyncio.sleep(0)
        finally:
            self._connections.discard(websocket)


class ControlClient:
    def __init__(self, uri: str) -> None:
        self.uri = uri
        self._socket: Optional[websockets.WebSocketClientProtocol] = None

    async def connect(self) -> None:
        self._socket = await websockets.connect(self.uri)

    async def disconnect(self) -> None:
        if self._socket:
            await self._socket.close()
            self._socket = None

    async def send(self, message_type: str, payload: dict, request_id: Optional[str] = None) -> None:
        if not self._socket:
            raise RuntimeError("ControlClient is not connected.")
        message = encode_message(message_type, payload, request_id=request_id)
        await self._socket.send(message)

    async def recv(self) -> dict:
        if not self._socket:
            raise RuntimeError("ControlClient is not connected.")
        raw_message = await self._socket.recv()
        return decode_message(raw_message)

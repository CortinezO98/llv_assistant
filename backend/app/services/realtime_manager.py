import asyncio
import json
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class RealtimeManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, event: dict):
        dead = []
        payload = json.dumps(event, ensure_ascii=False)

        for ws in self.active_connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    def broadcast_sync(self, event: dict):
        if not self.loop:
            logger.warning("Realtime loop no inicializado")
            return

        asyncio.run_coroutine_threadsafe(self.broadcast(event), self.loop)


realtime_manager = RealtimeManager()
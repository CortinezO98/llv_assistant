import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.services.realtime_manager import realtime_manager

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/realtime")
async def realtime_ws(websocket: WebSocket):
    token = websocket.query_params.get("token")

    if not token or not decode_token(token):
        await websocket.close(code=1008)
        return

    await realtime_manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        realtime_manager.disconnect(websocket)
    except Exception:
        realtime_manager.disconnect(websocket)
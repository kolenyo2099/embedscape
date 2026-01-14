"""
WebSocket handler for real-time progress updates
"""
import asyncio
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

router = APIRouter()

# Connected clients
_clients: Set[WebSocket] = set()


async def broadcast_progress(stage: str, progress: float, message: str, current: int = 0, total: int = 0):
    """Broadcast progress update to all connected clients"""
    if not _clients:
        return

    # Set type based on stage - 'complete' and 'error' are special types
    msg_type = stage if stage in ("complete", "error") else "progress"

    payload = json.dumps({
        "type": msg_type,
        "stage": stage,
        "progress": progress,
        "message": message,
        "current": current,
        "total": total
    })

    disconnected = set()
    for client in _clients:
        try:
            await client.send_text(payload)
        except Exception:
            disconnected.add(client)

    # Clean up disconnected clients
    for client in disconnected:
        _clients.discard(client)


@router.websocket("/ws/progress")
async def websocket_progress(websocket: WebSocket):
    """WebSocket endpoint for progress updates"""
    await websocket.accept()
    _clients.add(websocket)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to EmbedScape progress stream"
        })

        # Keep connection alive
        while True:
            try:
                # Wait for ping/pong or client disconnect
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")

            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for general events"""
    await websocket.accept()
    _clients.add(websocket)

    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to EmbedScape event stream"
        })

        while True:
            try:
                message = await websocket.receive_text()

                # Parse and handle commands
                try:
                    data = json.loads(message)
                    cmd = data.get("command")

                    if cmd == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif cmd == "subscribe":
                        await websocket.send_json({"type": "subscribed", "channel": data.get("channel")})

                except json.JSONDecodeError:
                    if message == "ping":
                        await websocket.send_text("pong")

            except WebSocketDisconnect:
                break

    finally:
        _clients.discard(websocket)


def get_client_count() -> int:
    """Get number of connected WebSocket clients"""
    return len(_clients)

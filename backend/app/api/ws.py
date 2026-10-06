import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Match
from app.services.progress import get_redis_client

router = APIRouter(tags=["websocket"])

@router.websocket("/ws/matches/{match_id}")
async def match_progress_websocket(
    websocket: WebSocket,
    match_id: UUID,
    db: Session = Depends(get_db)
):
    await websocket.accept()

    # Query initial match status from DB
    match_str = str(match_id)
    match_obj = db.query(Match).filter(Match.id == match_id).first()

    if not match_obj:
        await websocket.send_json({
            "status": "failed",
            "progress": 0,
            "message": "Match not found",
            "error": "Match not found"
        })
        await websocket.close()
        return

    # Send current state immediately on connect
    initial_payload = {
        "status": match_obj.status,
        "progress": match_obj.progress,
        "message": match_obj.progress_message,
        "error": match_obj.error_message
    }
    await websocket.send_json(initial_payload)

    # If already in terminal state, close connection cleanly
    if match_obj.status in ("completed", "failed"):
        await websocket.close()
        return

    # Subscribe to Redis pub/sub channel match:{id}:progress
    redis_cli = get_redis_client()
    pubsub = redis_cli.pubsub()
    channel_name = f"match:{match_str}:progress"
    pubsub.subscribe(channel_name)

    try:
        while True:
            # Non-blocking get message
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data_str = message.get("data")
                if data_str:
                    payload = json.loads(data_str)
                    await websocket.send_json(payload)
                    # If terminal state reached, break loop and close
                    if payload.get("status") in ("completed", "failed"):
                        break
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected from match {match_str}")
    except Exception as exc:
        print(f"[WebSocket] Error in websocket loop for match {match_str}: {exc}")
    finally:
        try:
            pubsub.unsubscribe(channel_name)
            pubsub.close()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass

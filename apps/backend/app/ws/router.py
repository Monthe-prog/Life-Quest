from __future__ import annotations

from jose import JWTError
from sqlalchemy import select

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models import ActivityEvent, User, UserProfile

router = APIRouter()


async def serialize_event(event: ActivityEvent) -> dict[str, object]:
    async with AsyncSessionLocal() as db:
        profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == event.user_id))
        payload = event.payload or {}
        return {
            "type": "battle_reward",
            "id": event.id,
            "operator": profile.callsign if profile and profile.callsign else "OPERATOR",
            "goal_title": payload.get("goal_title"),
            "xp_awarded": payload.get("xp_awarded"),
            "stat_key": payload.get("stat_key"),
            "created_at": event.created_at.isoformat(),
        }


@router.websocket("/guild-feed")
async def guild_feed(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = decode_token(token)
    except JWTError:
        await websocket.close(code=1008)
        return

    async with AsyncSessionLocal() as db:
        user = await db.get(User, payload.get("sub"))
        if user is None or payload.get("type") != "access":
            await websocket.close(code=1008)
            return

        await websocket.accept()
        await websocket.send_json({"type": "system", "message": "Global feed channel initialized."})
        result = await db.scalars(
            select(ActivityEvent)
            .where(ActivityEvent.event_type == "battle_reward")
            .order_by(ActivityEvent.created_at.desc())
            .limit(10)
        )
        for event in reversed(list(result)):
            await websocket.send_json(await serialize_event(event))

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return

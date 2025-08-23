import json
from datetime import datetime
from uuid import uuid4
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.db.sessions import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.chat import ChatParticipant, Message
from app.websockets.connection_manager import manager

router = APIRouter()

def get_user_from_token(token: str, db: Session) -> Optional[User]:
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None

@router.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str, token: str = Query(...)):

    await websocket.accept()

    db = next(get_db())
    current_user = get_user_from_token(token, db)
    if not current_user:
        await websocket.send_text(json.dumps({"type": "error", "detail": "Invalid or expired token"}))
        await websocket.close(code=4401)  # unauthorized
        return

    is_participant = db.query(ChatParticipant).filter_by(chat_id=chat_id, user_id=current_user.id).first()
    if not is_participant:
        await websocket.send_text(json.dumps({"type": "error", "detail": "Not a participant"}))
        await websocket.close(code=4403)  # forbidden
        return


    current_user.is_online = True
    db.commit()

    await manager.connect(chat_id, str(current_user.id), websocket)


    await manager.broadcast(chat_id, json.dumps({
        "type": "presence_update",
        "data": {
            "user_id": str(current_user.id),
            "is_online": True,
            "username": current_user.username,
            "last_seen": None
        }
    }), exclude=websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if "ping" in data:
                await websocket.send_text(json.dumps({"type": "pong", "ts": data["ping"]}))
                continue


            if "is_typing" in data:
                await manager.broadcast(chat_id, json.dumps({
                    "type": "typing_status",
                    "data": {
                        "user_id": str(current_user.id),
                        "username": current_user.username,
                        "is_typing": bool(data["is_typing"])
                    }
                }), exclude=websocket)
                continue


            content = (data.get("content") or "").strip()


            msg = Message(
                id=uuid4(),
                chat_id=chat_id,
                sender_id=current_user.id,
                content=content
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)

            await manager.broadcast(chat_id, json.dumps({
                "type": "new_message",
                "data": {
                    "message_id": str(msg.id),
                    "chat_id": str(msg.chat_id),
                    "sender_id": str(msg.sender_id),
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat()
                }
            }))

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            manager.disconnect(chat_id, websocket)
            current_user.is_online = False
            current_user.last_seen = datetime.utcnow()
            db.commit()
            await manager.broadcast(chat_id, json.dumps({
                "type": "presence_update",
                "data": {
                    "user_id": str(current_user.id),
                    "is_online": False,
                    "username": current_user.username,
                    "last_seen": current_user.last_seen.isoformat()
                }
            }))
        except Exception:
            pass

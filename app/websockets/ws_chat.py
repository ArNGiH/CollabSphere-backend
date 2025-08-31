import json
from datetime import datetime
from uuid import uuid4
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
import uuid

from app.db.sessions import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.chat import ChatParticipant, Message, Chat, ChatType
from app.websockets.connection_manager import manager
from app.services.ai_service import get_ai_reply

router = APIRouter()

# Fixed AI user UUID (make sure you handle this in history responses)
AI_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


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
        await websocket.send_text(json.dumps({
            "type": "error",
            "detail": "Invalid or expired token"
        }))
        await websocket.close(code=4401)
        return

    # check participation
    is_participant = db.query(ChatParticipant).filter_by(
        chat_id=chat_id, user_id=current_user.id
    ).first()
    if not is_participant:
        await websocket.send_text(json.dumps({
            "type": "error",
            "detail": "Not a participant"
        }))
        await websocket.close(code=4403)
        return

    chat = db.query(Chat).filter_by(id=chat_id).first()
    if not chat:
        await websocket.send_text(json.dumps({
            "type": "error",
            "detail": "Chat not found"
        }))
        await websocket.close(code=4404)
        return

    # mark online
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

            # encrypted message (frontend must send both)
            encrypted_content = data.get("encrypted_content")
            encrypted_keys = data.get("encrypted_keys")

            if not encrypted_content or not encrypted_keys:
                continue  
            user_msg = Message(
                id=uuid4(),
                chat_id=chat_id,
                sender_id=current_user.id,
                encrypted_content=encrypted_content,
                encrypted_keys=encrypted_keys,
            )
            db.add(user_msg)
            db.commit()
            db.refresh(user_msg)

            # broadcast new message
            await manager.broadcast(chat_id, json.dumps({
                "type": "new_message",
                "data": {
                    "message_id": str(user_msg.id),
                    "chat_id": str(user_msg.chat_id),
                    "sender_id": str(user_msg.sender_id),
                    "encrypted_content": user_msg.encrypted_content,
                    "encrypted_keys": user_msg.encrypted_keys,
                    "created_at": user_msg.created_at.isoformat()
                }
            }))

            if chat.type == ChatType.ai:
                try:
                    await manager.broadcast(chat_id, json.dumps({
                        "type": "typing_status",
                        "data": {
                            "user_id": str(AI_USER_ID),
                            "username": "AI Assistant",
                            "is_typing": True
                        }
                    }))

                    # build history
                    history_messages = (
                        db.query(Message)
                        .filter(Message.chat_id == chat_id)
                        .order_by(Message.created_at.desc())
                        .limit(10)
                        .all()
                    )
                    history = []
                    for m in reversed(history_messages):
                        role = "assistant" if m.sender_id == AI_USER_ID else "user"
                        history.append({"role": role, "content": m.encrypted_content})

                    # AI reply
                    reply = await get_ai_reply(encrypted_content, history=history)

                    ai_msg = Message(
                        id=uuid4(),
                        chat_id=chat_id,
                        sender_id=AI_USER_ID,
                        encrypted_content=reply,
                        encrypted_keys={}, 
                    )
                    db.add(ai_msg)
                    db.commit()
                    db.refresh(ai_msg)

                    await manager.broadcast(chat_id, json.dumps({
                        "type": "new_message",
                        "data": {
                            "message_id": str(ai_msg.id),
                            "chat_id": str(ai_msg.chat_id),
                            "sender_id": str(AI_USER_ID),
                            "encrypted_content": ai_msg.encrypted_content,
                            "encrypted_keys": ai_msg.encrypted_keys,
                            "created_at": ai_msg.created_at.isoformat()
                        }
                    }))

                    await manager.broadcast(chat_id, json.dumps({
                        "type": "typing_status",
                        "data": {
                            "user_id": str(AI_USER_ID),
                            "username": "AI Assistant",
                            "is_typing": False
                        }
                    }))

                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "detail": f"AI reply failed: {str(e)}"
                    }))

    except WebSocketDisconnect:
        pass
    finally:
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
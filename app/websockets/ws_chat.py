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
        await websocket.close(code=4401)  # unauthorized
        return

    is_participant = db.query(ChatParticipant).filter_by(
        chat_id=chat_id, user_id=current_user.id
    ).first()
    if not is_participant:
        await websocket.send_text(json.dumps({
            "type": "error",
            "detail": "Not a participant"
        }))
        await websocket.close(code=4403)  # forbidden
        return

    chat = db.query(Chat).filter_by(id=chat_id).first()
    if not chat:
        await websocket.send_text(json.dumps({
            "type": "error",
            "detail": "Chat not found"
        }))
        await websocket.close(code=4404)  # not found
        return

    # Mark user online
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

            # Handle ping/pong
            if "ping" in data:
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "ts": data["ping"]
                }))
                continue

            # Handle typing indicator
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

            # Handle regular messages
            content = (data.get("content") or "").strip()
            if not content:
                continue

            # Save user message
            user_msg = Message(
                id=uuid4(),
                chat_id=chat_id,
                sender_id=current_user.id,
                content=content
            )
            db.add(user_msg)
            db.commit()
            db.refresh(user_msg)

            # Broadcast user message
            await manager.broadcast(chat_id, json.dumps({
                "type": "new_message",
                "data": {
                    "message_id": str(user_msg.id),
                    "chat_id": str(user_msg.chat_id),
                    "sender_id": str(user_msg.sender_id),
                    "content": user_msg.content,
                    "created_at": user_msg.created_at.isoformat()
                }
            }))

            # Handle AI chat
            if chat.type == ChatType.ai:
                try:
                    # Broadcast typing start
                    await manager.broadcast(chat_id, json.dumps({
                        "type": "typing_status",
                        "data": {
                            "user_id": str(AI_USER_ID),
                            "username": "AI Assistant",
                            "is_typing": True
                        }
                    }))

                    # Fetch recent history for context
                    history_messages = (
                        db.query(Message)
                        .filter(Message.chat_id == chat_id)
                        .order_by(Message.created_at.desc())
                        .limit(10)
                        .all()
                    )

                    history = []
                    for m in reversed(history_messages): 
                        if m.sender_id == AI_USER_ID:
                            role = "assistant"
                        else:
                            role = "user"
                        history.append({"role": role, "content": m.content})

                    # Get AI reply
                    reply = await get_ai_reply(content, history=history)

                    # Save AI message
                    ai_msg = Message(
                        id=uuid4(),
                        chat_id=chat_id,
                        sender_id=AI_USER_ID,
                        content=reply
                    )
                    db.add(ai_msg)
                    db.commit()
                    db.refresh(ai_msg)

                    # Broadcast AI message
                    await manager.broadcast(chat_id, json.dumps({
                        "type": "new_message",
                        "data": {
                            "message_id": str(ai_msg.id),
                            "chat_id": str(ai_msg.chat_id),
                            "sender_id": str(AI_USER_ID),
                            "content": ai_msg.content,
                            "created_at": ai_msg.created_at.isoformat()
                        }
                    }))

                    # Broadcast typing end
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

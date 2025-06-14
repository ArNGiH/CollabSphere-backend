import json 
from uuid import uuid4
from app.models.chat import Message
from app.db.sessions import get_db
from jose import JWTError
from app.core.security import decode_access_token
from app.models.user import User
from sqlalchemy.orm import Session
from app.models.chat import ChatParticipant
from fastapi import APIRouter,WebSocket,WebSocketDisconnect,Query
from app.websockets.connection_manager import manager

async def get_user_from_token(token:str,db:Session):
    try:
        payload=decode_access_token(token)
        print(payload)
        user_id=payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id==user_id).first()
    except Exception:
        return None
    



router=APIRouter()

@router.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint(websocket:WebSocket,chat_id:str,token:str=Query(...)):
    print("🟢 WebSocket connected")
    print("Token received:", token)

    db = next(get_db())


    current_user=await get_user_from_token(token,db)

    if not current_user:
        await websocket.send_text(
            json.dumps({
                "type":"error",
                "detail":"Invalid or expired token"
            })
        )
        await websocket.close()
        return 
    await manager.connect(chat_id,websocket)
   

    try:
        while True:
            raw_data=await websocket.receive_text()
            data=json.loads(raw_data)
            if "content" not in data:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "detail": "Missing message content"
                }))
                continue

            is_participant = db.query(ChatParticipant).filter_by(
                chat_id=chat_id,
                user_id=current_user.id
            ).first()
            if not is_participant:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "detail": "You are not a participant of this chat"
                }))
                continue

            message = Message(
                id=uuid4(),
                chat_id=chat_id,
                sender_id=current_user.id,
                content=data["content"]
            )
            db.add(message)
            db.commit()
            db.refresh(message)

            payload = {
                "type":"new_message",
                "data":{
                    "message_id":str(message.id),
                     "chat_id": str(message.chat_id),
                    "sender_id": str(message.sender_id),
                    "content": message.content,
                    "created_at": message.created_at.isoformat()
                }
            }
            await manager.broadcast(chat_id,json.dumps(payload))

    except Exception as e:
        print(f"❌ Error in WebSocket loop: {e}")
        manager.disconnect(chat_id, websocket)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.sessions import get_db
from app.core.security import get_current_user
from app.schemas.ai import AIChatRequest, AIChatResponse
from app.services.ai_service import get_ai_reply
from app.models.chat import Chat, Message
from uuid import uuid4

router = APIRouter(tags=["AI"], prefix="/ai")

@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    req: AIChatRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    chat = db.query(Chat).filter(Chat.id == req.chat_id).first()
    if not chat or chat.type != "ai":
        raise HTTPException(status_code=400, detail="Not an AI chat")


    user_msg = Message(id=uuid4(), chat_id=req.chat_id, sender_id=current_user.id, content=req.message)
    db.add(user_msg)
    db.commit()

    
    reply = await get_ai_reply(req.message)

    
    ai_msg = Message(id=uuid4(), chat_id=req.chat_id, sender_id=None, content=reply)
    db.add(ai_msg)
    db.commit()


    return AIChatResponse(reply=reply)

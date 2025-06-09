from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.sessions import get_db
from app.core.security import get_current_user
from app.models.chat import Chat,ChatParticipant
from app.models.user import User
from app.schemas.chat import CreateChatRequest,ChatDetail
from uuid import uuid4

router = APIRouter(tags=["Chat"],prefix="/chat")


@router.post("/create-new-chat",response_model=ChatDetail)
def create_chat(
        chat_data:CreateChatRequest,
        db:Session=Depends(get_db),
        current_user: User=Depends(get_current_user)
):
    if current_user.id not in chat_data.participant_ids:
        chat_data.participant_ids.append(current_user.id)

    
    new_chat=Chat(
        id=uuid4(),
        name=chat_data.name,
        type=chat_data.type
    )
    db.add(new_chat)
    db.flush()

    for user_id in chat_data.participant_ids:
        participant=ChatParticipant(user_id=user_id,chat_id=new_chat.id)
        db.add(participant)

    db.commit()
    db.refresh(new_chat)

    return ChatDetail(
        id=new_chat.id,
        name=new_chat.name,
        type=new_chat.type,
        created_at=new_chat.created_at,
        participants=chat_data.participant_ids

    )
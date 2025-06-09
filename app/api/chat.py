from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.orm import Session
from app.db.sessions import get_db
from app.core.security import get_current_user
from app.models.chat import Chat,ChatParticipant,Message
from app.models.user import User
from app.schemas.chat import CreateChatRequest,ChatDetail,ChatHistoryResponse,ChatType
from app.schemas.messages import MessageResponse,SendMessageRequest,FullMessageResponse
from uuid import uuid4
from typing import List
from uuid import UUID


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


@router.post("/send-message",response_model=MessageResponse)
def send_message(
    message_data:SendMessageRequest,
    db:Session=Depends(get_db),
    current_user:User=Depends(get_current_user)
):
    chat = db.query(Chat).filter(Chat.id == message_data.chat_id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat does not exist"
        )
    
    participant=db.query(ChatParticipant).filter_by(
        chat_id=message_data.chat_id,
        user_id=current_user.id
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You are not a participant of this chat'
        )
    
    new_message=Message(
        id=uuid4(),
        chat_id=message_data.chat_id,
        sender_id=current_user.id,
        content=message_data.content
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return new_message

@router.get("/current-chats",response_model=List[ChatHistoryResponse])
def get_user_chats(
    db:Session=Depends(get_db),
    current_user:User=Depends(get_current_user)
):
    chat_ids=db.query(ChatParticipant.chat_id).filter_by(user_id=current_user.id).subquery()
    chats = db.query(Chat).filter(Chat.id.in_(chat_ids)).order_by(Chat.created_at.desc()).all()

    response=[]
    for chat in chats:
        other_user_id:None
        other_user_name:None
        other_user_image:None

        if chat.type==ChatType.private:
            participants=[p.user_id for p in chat.participants]
            other_id=next((uid for uid in participants if uid!=current_user.id),None)
            if other_id:
                other_user=db.query(User).filter(User.id==other_id).first()
                if other_user:
                    other_user_id=other_user.id
                    other_user_name=other_user.full_name or other_user.username
                    other_user_image=other_user.profile_image

        display_name=chat.name
        if chat.type==ChatType.private:
            display_name=other_user_name

        response.append(ChatHistoryResponse(
        id=chat.id,
        name=display_name,
        type=chat.type,
        created_at=chat.created_at,
        other_user_id=other_user_id,
        other_user_name=other_user_name,
        other_user_image=other_user_image
    ))

    return response


@router.get("/history/{chat_id}",response_model=List[FullMessageResponse])
def get_chat_history(
    chat_id:UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)

):
    is_participant=db.query(ChatParticipant).filter_by(
        chat_id=chat_id,
        user_id=current_user.id
    ).first()

    if not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You are not authorized to view this chat'
        )
    
    messages=db.query(Message).filter_by(chat_id=chat_id).order_by(Message.created_at.asc()).all()
    response=[]

    for message in messages:
        sender=db.query(User).filter_by(id=message.sender_id).first()
        response.append(FullMessageResponse(
            id=message.id,
            chat_id=message.chat_id,
            sender_id=message.sender_id,
            sender_name=sender.full_name or sender.username,
            content=message.content,
            created_at=message.created_at
        ))
    return response
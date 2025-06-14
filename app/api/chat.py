from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.orm import Session
from app.db.sessions import get_db
from app.core.security import get_current_user
from app.models.chat import Chat,ChatParticipant,Message
from app.models.user import User
from app.schemas.chat import CreateChatRequest,ChatDetail,ChatHistoryResponse,ChatType
from app.schemas.messages import MessageResponse,SendMessageRequest,FullMessageResponse,EditMessageRequest
from app.schemas.pinned_message import PinnedMessageResponse
from app.models.pinned_message import PinnedMessage
from datetime import datetime
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
    
    messages_query=db.query(Message).filter(Message.chat_id==chat_id)

    if is_participant.last_deleted_at:
        messages_query=messages_query.filter(Message.created_at>is_participant.last_deleted_at)

    messages = messages_query.order_by(Message.created_at.asc()).all()
    
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


@router.delete("/clear-messages/{chat_id}")
def clear_chat_history(
    chat_id:UUID,
    db:Session=Depends(get_db),
    current_user:User=Depends(get_current_user),
):
    participant=db.query(ChatParticipant).filter_by(chat_id=chat_id,user_id=current_user.id).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found for user"
        )
    
    participant.last_deleted_at=datetime.utcnow()
    db.commit()

    return {"detail":"Chat history deleted"}


@router.delete("/delete_message/{message_id}")
def delete_message(
    message_id,
    db:Session=Depends(get_db),
    current_user:User=Depends(get_current_user)
):
    message=db.query(Message).filter(Message.id==message_id).first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    if message.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this message"
        )
    
    db.delete(message)
    db.commit()

    return {"detail": "Message deleted successfully"}
    
@router.put("/edit-message/{message_id}",response_model=MessageResponse)
def edit_message(
    message_id:UUID,
    message_data:EditMessageRequest,
    db:Session=Depends(get_db),
    current_user:User=Depends(get_current_user)
):
    message=db.query(Message).filter(Message.id==message_id).first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    if message.sender_id !=current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to edit this message"
        )
    message.is_edited=True
    message.content=message_data.content
    db.commit()
    db.refresh(message)
    return message

@router.post("/pin-message/{message_id}")
def pin_message(
    message_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = db.query(Message).filter_by(id=message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    is_participant = db.query(ChatParticipant).filter_by(
        chat_id=message.chat_id, user_id=current_user.id
    ).first()
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not allowed to pin in this chat")

    already_pinned = db.query(PinnedMessage).filter_by(message_id=message_id).first()
    if already_pinned:
        raise HTTPException(status_code=400, detail="Message already pinned")

    pin = PinnedMessage(message_id=message_id, chat_id=message.chat_id)
    db.add(pin)
    db.commit()
    return {"detail": "Message pinned"}

@router.get("/pinned-messages/{chat_id}/", response_model=List[PinnedMessageResponse])
def get_pinned_messages(
    chat_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_participant = db.query(ChatParticipant).filter_by(
        chat_id=chat_id, user_id=current_user.id
    ).first()
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not allowed")

    pins = (
        db.query(PinnedMessage)
        .filter_by(chat_id=chat_id)
        .order_by(PinnedMessage.pinned_at.desc())
        .all()
    )
    return pins

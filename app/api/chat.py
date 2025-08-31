from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.orm import Session,joinedload
from sqlalchemy import desc
from app.db.sessions import get_db
from app.core.security import get_current_user
from app.models.chat import Chat,ChatParticipant,Message
from app.models.user import User
from app.schemas.chat import CreateChatRequest,ChatDetail,ChatHistoryResponse,ChatType,ChatParticipantMini,ChatSummaryMinimal
from app.schemas.messages import MessageResponse,SendMessageRequest,FullMessageResponse,EditMessageRequest
from app.schemas.pinned_message import PinnedMessageResponse
from app.models.pinned_message import PinnedMessage
from datetime import datetime
from uuid import uuid4
from typing import List
import uuid
from uuid import UUID


router = APIRouter(tags=["Chat"],prefix="/chat")
AI_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

@router.post("/create-new-chat",response_model=ChatDetail)
def create_chat(
        chat_data:CreateChatRequest,
        db:Session=Depends(get_db),
        current_user: User=Depends(get_current_user)
):
    if current_user.id not in chat_data.participant_ids:
        chat_data.participant_ids.append(current_user.id)

    if chat_data.type == ChatType.ai:
        chat_data.participant_ids = [current_user.id, AI_USER_ID]


    
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
        encrypted_content=message_data.encrypted_content,
        encrypted_keys=message_data.encrypted_keys
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return new_message

@router.get("/current-chats", response_model=List[ChatSummaryMinimal])
def get_user_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    chats = (
        db.query(Chat)
        .join(ChatParticipant, ChatParticipant.chat_id == Chat.id)
        .filter(ChatParticipant.user_id == current_user.id)
        .options(
            joinedload(Chat.participants).joinedload(ChatParticipant.user)  # eager-load users
        )
        .order_by(desc(Chat.created_at))
        .all()
    )

    response: List[ChatSummaryMinimal] = []

    for chat in chats:
        # "Others" in this chat (exclude current user)
        others = [p.user for p in chat.participants if p.user_id != current_user.id]

        # Minimal participant payload
        participants = [
            ChatParticipantMini(
                id=u.id,
                display_name=(u.full_name or u.username),
                avatar_url=u.profile_image,
                public_key=u.public_key
            )
            for u in others
        ]

        # Display name for list/header
        if chat.type == ChatType.private:
            # DM: show the other user’s name
            display_name = participants[0].display_name if participants else (chat.name or "Private")
            name_for_groups = None
        else:
            # Group: show chat.name (fallback if empty)
            display_name = chat.name or "Group"
            name_for_groups = chat.name

        response.append(
            ChatSummaryMinimal(
                id=chat.id,
                type=chat.type.value if hasattr(chat.type, "value") else chat.type,  # tolerate enum or str
                display_name=display_name,
                name=name_for_groups,
                participants=participants,
                created_at=chat.created_at,
            )
        )

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
            encrypted_content=message.encrypted_content,
            created_at=message.created_at,
            media_type=message.media_type,
            media_url=message.media_url,
            sender_public_key=sender.public_key
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
    message.encrypted_content = message_data.content
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

from sqlalchemy import Column, String, Boolean , DateTime ,Enum,ForeignKey,Text,JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid
from app.db.base import Base


class ChatType(str,enum.Enum):
    PRIVATE="private"
    GROUP="group"
    ai="ai"


class Chat(Base):
    __tablename__ = "chats"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name= Column(String, nullable=True)
    type=Column(Enum(ChatType),default=ChatType.PRIVATE)
    created_at=Column(DateTime,default=datetime.utcnow)

    participants=relationship("ChatParticipant",back_populates="chat")
    messages= relationship("Message",back_populates="chat")


class ChatParticipant(Base):
    __tablename__="chat_participants"
    user_id=Column(UUID(as_uuid=True),ForeignKey("users.id"),primary_key=True)
    chat_id=Column(UUID(as_uuid=True),ForeignKey("chats.id"),primary_key=True)
    last_deleted_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="chat_participations")
    chat = relationship("Chat", back_populates="participants")


class Message(Base):
    __tablename__="messages"
    id=Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    chat_id=Column(UUID(as_uuid=True),ForeignKey("chats.id"),index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),index=True)
    #content=Column(Text,nullable=True)
    encrypted_content = Column(Text, nullable=False)
    encrypted_keys = Column(JSON, nullable=False)  # {user_id: encryptedAES}
    created_at=Column(DateTime,default=datetime.utcnow)
    media_url = Column(String, nullable=True)  # ➕ NEW
    media_type = Column(String, nullable=True)
    is_edited=Column(Boolean,default=False)

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="messages_sent")
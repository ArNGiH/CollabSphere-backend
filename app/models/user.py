import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class User(Base):
    __tablename__='users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    email=Column(String, unique=True,index=True,nullable=False)
    username=Column(String, unique=True, nullable=False)
    full_name=Column(String, nullable=True)


    #Auth
    hashed_password=Column(String, nullable=False)
    is_active=Column(Boolean,default=True)
    is_verified=Column(Boolean,default=False)
    is_superuser=Column(Boolean,default=False)

    #Employee info & Status
    profile_image=Column(String,nullable=True)
    status_message=Column(String,nullable=True)
    is_online= Column(Boolean,default=False)
    last_seen=Column(DateTime,nullable=True)

    #Audit Fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    chat_participations = relationship("ChatParticipant", back_populates="user")
    messages_sent = relationship("Message", back_populates="sender")




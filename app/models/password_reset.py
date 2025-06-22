import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class PasswordResetToken(Base):
    __tablename__="password_reset_tokens"
    
    id=Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    token=Column(String,unique=True,nullable=False)
    user_id=Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=False)
    created_at=Column(DateTime(timezone=True),server_default=func.now())
    expires_at=Column(DateTime(timezone=True),nullable=False)

    user=relationship("User")
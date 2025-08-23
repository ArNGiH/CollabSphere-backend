from pydantic import BaseModel , UUID4
from typing import Optional
from datetime import datetime


class UserSummary(BaseModel):
    id: UUID4
    username: str
    full_name: Optional[str] = None
    profile_image: Optional[str] = None 
    is_online: bool
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes=True


# app/schemas/user.py

from pydantic import BaseModel, EmailStr, UUID4
from typing import Optional
from datetime import datetime


class UserDetail(BaseModel):
    id: UUID4
    email: EmailStr
    username: str
    full_name: Optional[str]
    profile_image: Optional[str]
    status_message: Optional[str]
    is_online: bool
    last_seen: Optional[datetime]
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

from pydantic import BaseModel, EmailStr, constr
from typing import Optional,Annotated
from uuid import UUID
from datetime import datetime


PasswordStr = Annotated[str, constr(min_length=6)]

class RegisterRequest(BaseModel):
    email:EmailStr
    username:str
    full_name:Optional[str]
    password:PasswordStr


class LoginRequest(BaseModel):
    email:EmailStr
    password:str


class RegisterResponse(BaseModel):
    message:str='Account created . Please verify your email to login '
    user_id: Optional[UUID]
    email_sent: bool = True


class UserResponse(BaseModel):
    id:UUID
    email:EmailStr
    username:Optional[str]
    full_name:Optional[str]
    profile_image:Optional[str]
    status_message:Optional[str]
    is_active:bool
    is_verified:bool
    is_superuser:bool
    created_at:datetime
    updated_at:Optional[datetime]

    class Config:
        from_attributes = True
     
    
class LoginResponse(BaseModel):
    access_token:str
    user:UserResponse

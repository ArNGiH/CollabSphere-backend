from pydantic import BaseModel,UUID4
from datetime import datetime
from typing import Dict, Optional
from pydantic import Field
from uuid import UUID

class SendMessageRequest(BaseModel):
    chat_id:UUID
    encrypted_content: str
    encrypted_keys: Dict[str, str]

class MessageResponse(BaseModel):
    id:UUID
    chat_id:UUID
    sender_id:UUID
    created_at:datetime
    encrypted_content: str
    encrypted_keys: Dict[str, str]
    is_edited: bool = Field(default=False)


    class Config:
        from_attributes = True

class FullMessageResponse(MessageResponse):
    sender_name: Optional[str]=None
    sender_image: Optional[str]=None
    media_type:Optional[str]=None
    media_url:Optional[str]=None
    sender_public_key: Optional[str] = None


class EditMessageRequest(BaseModel):
    content:str


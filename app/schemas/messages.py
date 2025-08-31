from pydantic import BaseModel,UUID4
from datetime import datetime
from typing import Optional
from pydantic import Field
from uuid import UUID

class SendMessageRequest(BaseModel):
    chat_id:UUID
    content:str

class MessageResponse(BaseModel):
    id:UUID
    chat_id:UUID
    sender_id:UUID
    content:Optional[str]
    created_at:datetime
    is_edited: bool = Field(default=False)


    class Config:
        from_attributes = True

class FullMessageResponse(MessageResponse):
    sender_name: Optional[str]=None
    sender_image: Optional[str]=None
    media_type:Optional[str]=None
    media_url:Optional[str]=None


class EditMessageRequest(BaseModel):
    content:str


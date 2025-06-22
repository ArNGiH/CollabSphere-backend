from pydantic import BaseModel,UUID4
from datetime import datetime
from typing import Optional
from pydantic import Field

class SendMessageRequest(BaseModel):
    chat_id:UUID4
    content:str

class MessageResponse(BaseModel):
    id:UUID4
    chat_id:UUID4
    sender_id:UUID4
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


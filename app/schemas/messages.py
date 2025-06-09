from pydantic import BaseModel,UUID4
from datetime import datetime
from typing import Optional

class SendMessageRequest(BaseModel):
    chat_id:UUID4
    content:str

class MessageResponse(BaseModel):
    id:UUID4
    chat_id:UUID4
    sender_id:UUID4
    content:Optional[str]
    created_at:datetime


    class Config:
        from_attributes = True

class FullMessageResponse(MessageResponse):
    sender_name: Optional[str]=None
    sender_image: Optional[str]=None


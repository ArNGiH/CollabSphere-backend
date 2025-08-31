from pydantic import BaseModel 
from uuid import UUID
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum

class ChatType(str,Enum):
    private="private"
    group="group"
    ai="ai"

class CreateChatRequest(BaseModel):
    name:Optional[str]
    type:ChatType
    participant_ids:List[UUID]


class ChatSummary(BaseModel):
    id:UUID
    name:Optional[str]
    type:ChatType
    created_at:datetime

    class Config:
        from_attributes = True

class ChatDetail(ChatSummary):
    participants:List[UUID]

class ChatHistoryResponse(BaseModel):
    id:UUID
    name:Optional[str]
    type:ChatType
    created_at:datetime

    other_user_id: Optional[UUID] = None
    other_user_name: Optional[str] = None
    other_user_image: Optional[str] = None

    class Config:
        from_attributes = True




class ChatParticipantMini(BaseModel):
    id: UUID
    display_name: str
    avatar_url: Optional[str] = None

    class Config:
        orm_mode = True 

class ChatSummaryMinimal(BaseModel):
    id: UUID
    type: Literal['private', 'group', 'ai']
    display_name: str             
    name: Optional[str] = None   
    participants: List[ChatParticipantMini]
    created_at: datetime

    class Config:
        orm_mode = True
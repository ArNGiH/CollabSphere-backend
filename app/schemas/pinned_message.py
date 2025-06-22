from pydantic import BaseModel, UUID4
from datetime import datetime

class PinnedMessageResponse(BaseModel):
    id:UUID4
    chat_id:UUID4
    message_id:UUID4
    pinned_at:datetime

    class Config:
        from_attributes=True
from pydantic import BaseModel,UUID4

class AIChatRequest(BaseModel):
    chat_id: UUID4
    message: str
class AIChatResponse(BaseModel):
    reply: str

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models.conversation_model import ConversationStatus


class ConversationCreate(BaseModel):
    utilisateur_id: int
    service_id: int
    bot_id: Optional[int] = None


class ConversationOut(BaseModel):
    conversationid: int
    utilisateur_id: Optional[int]
    service_id: Optional[int]
    bot_id: Optional[int]
    start_time: datetime
    end_time: Optional[datetime]
    last_activity: datetime
    status: ConversationStatus
    notes: Optional[str]
    titre: Optional[str]

    class Config:
        from_attributes = True

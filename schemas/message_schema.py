from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models.enums import MessageTypeEnum, PriorityEnum


class MessageCreate(BaseModel):
    conversation_id: int
    contenu: str
    type_message: MessageTypeEnum
    langue: str = "fr"
    type_question: Optional[str] = None
    feedback: Optional[int] = None
    feedback_text: Optional[str] = None
    priority: Optional[PriorityEnum] = PriorityEnum.medium


class MessageOut(BaseModel):
    messageId: int
    conversation_id: Optional[int]
    contenu: str
    type_message: MessageTypeEnum
    timestamp: Optional[datetime]
    langue: str
    type_question: Optional[str]
    feedback: Optional[int]
    feedback_text: Optional[str]
    priority: Optional[PriorityEnum]
    temp_document_ids: Optional[str] = None

    class Config:
        from_attributes = True

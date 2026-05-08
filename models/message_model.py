from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Interval, Enum as SAEnum
from sqlalchemy.orm import relationship
from .base import Base
from .enums import MessageTypeEnum, PriorityEnum


class Message(Base):
    __tablename__ = "message"

    messageId       = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversation.conversationid", ondelete="CASCADE"))
    contenu         = Column(Text, nullable=False)
    type_message    = Column(SAEnum(MessageTypeEnum, name="message_type_enum"), nullable=False)
    timestamp       = Column(DateTime, default=lambda: datetime.now(UTC))
    langue          = Column(String(10), default="fr", nullable=False)
    type_question   = Column(String(30), nullable=True)
    feedback        = Column(Integer, nullable=True)
    feedback_text   = Column(String(255), nullable=True)
    response_time   = Column(Interval, nullable=True)
    priority        = Column(SAEnum(PriorityEnum, name="priority_enum"), default=PriorityEnum.medium, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")

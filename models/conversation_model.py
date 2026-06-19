import enum
from datetime import datetime, UTC, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from .base import Base


class ConversationStatus(str, enum.Enum):
    active   = "active"
    closed   = "closed"


class ConversationEventType(str, enum.Enum):
    created  = "created"
    closed   = "closed"
    reopened = "reopened"
    noted    = "noted"


class Conversation(Base):
    __tablename__ = "conversation"

    conversationid = Column(Integer, primary_key=True, autoincrement=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateur.utilisateurId", ondelete="CASCADE"))
    service_id     = Column(Integer, ForeignKey("service.serviceId"))
    bot_id         = Column(Integer, ForeignKey("bot.botId"))
    start_time     = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    end_time       = Column(DateTime, nullable=True)
    last_activity  = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    status         = Column(SAEnum(ConversationStatus, name="conversation_status"), default=ConversationStatus.active, nullable=False)
    notes          = Column(Text, nullable=True)
    titre          = Column(String(255), nullable=True)

    utilisateur    = relationship("Utilisateur", back_populates="conversations")
    service        = relationship("Service", back_populates="conversations")
    bot            = relationship("Bot", back_populates="conversations")
    messages       = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    temp_documents = relationship("ConversationTempDocument", back_populates="conversation", cascade="all, delete-orphan")
    events         = relationship("ConversationEvent", back_populates="conversation", cascade="all, delete-orphan")


class ConversationTempDocument(Base):
    __tablename__ = "conversation_temp_document"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversation.conversationid", ondelete="CASCADE"), nullable=False)
    filename        = Column(String(255), nullable=True)
    filepath        = Column(Text, nullable=False)
    uploaded_at     = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    expires_at      = Column(DateTime, default=lambda: datetime.now(UTC) + timedelta(hours=1), nullable=False)
    uploaded_by     = Column(Integer, ForeignKey("utilisateur.utilisateurId"), nullable=True)

    conversation = relationship("Conversation", back_populates="temp_documents")
    utilisateur  = relationship("Utilisateur")


class ConversationEvent(Base):
    __tablename__ = "conversation_event"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversation.conversationid", ondelete="CASCADE"), nullable=False)
    event_type      = Column(SAEnum(ConversationEventType, name="conversation_event_type"), nullable=False)
    utilisateur_id  = Column(Integer, ForeignKey("utilisateur.utilisateurId"), nullable=True)
    timestamp       = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    details         = Column(Text, nullable=True)

    conversation = relationship("Conversation", back_populates="events")
    utilisateur  = relationship("Utilisateur")

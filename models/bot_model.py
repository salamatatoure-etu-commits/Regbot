import enum
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import relationship
from .base import Base


class BotStatus(str, enum.Enum):
    active  = "active"
    blocked = "blocked"


class Bot(Base):
    __tablename__ = "bot"

    botId        = Column(Integer, primary_key=True, autoincrement=True)
    nom          = Column(String(100), nullable=False)
    service_id   = Column(Integer, ForeignKey("service.serviceId"))
    langue       = Column(String(10), default="fr")
    actif        = Column(Boolean, default=True)
    status       = Column(SAEnum(BotStatus, name="bot_status"), default=BotStatus.active, nullable=False)
    api_key      = Column(Text, unique=True, nullable=True)
    prompt       = Column(Text, nullable=True)
    llm_model_id = Column(Integer, ForeignKey("llm_model.llmId"), nullable=True)
    created_at   = Column(DateTime, nullable=False, server_default=func.now())
    updated_at   = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    service       = relationship("Service", back_populates="bot")
    conversations = relationship("Conversation", back_populates="bot")
    llm_model     = relationship("LLMModel", back_populates="bots")

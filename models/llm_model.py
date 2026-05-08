from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from .base import Base


class LLMModel(Base):
    __tablename__ = "llm_model"
    llmId          = Column(Integer, primary_key=True)
    name        = Column(String(100), unique=True, nullable=False)
    api_name    = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    entry_tokens = Column(Integer, nullable=True, comment='Maximum input tokens for this model')
    sortie_tokens = Column(Integer, nullable=True, comment='Maximum output tokens for this model')

    bots = relationship("Bot", back_populates="llm_model")

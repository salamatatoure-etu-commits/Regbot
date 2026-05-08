from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .base import Base


class Service(Base):
    __tablename__ = "service"

    serviceId   = Column(Integer, primary_key=True)
    nom         = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))

    utilisateurs  = relationship("Utilisateur", back_populates="service")
    bot           = relationship("Bot", back_populates="service", uselist=False)
    documents     = relationship("Document", back_populates="service")
    conversations = relationship("Conversation", back_populates="service")

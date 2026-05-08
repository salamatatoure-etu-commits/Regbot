from datetime import datetime, UTC
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateur.utilisateurId", ondelete="CASCADE"), nullable=False)
    token          = Column(Text, nullable=False, unique=True)
    created_at     = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    expires_at     = Column(DateTime, nullable=False)

    utilisateur = relationship("Utilisateur", back_populates="refresh_tokens")

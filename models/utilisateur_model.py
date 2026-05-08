from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base
from .enums import RoleEnum


class Utilisateur(Base):
    __tablename__ = "utilisateur"
    __table_args__ = (UniqueConstraint("email", name="uq_email"),)

    utilisateurId = Column(Integer, primary_key=True, autoincrement=True)
    nom           = Column(String(100), nullable=False)
    email         = Column(String(150), nullable=False)
    mot_de_passe  = Column(String(255), nullable=False)
    role          = Column(SAEnum(RoleEnum, name="role_enum"), nullable=False)
    service_id    = Column(Integer, ForeignKey("service.serviceId"))
    is_active     = Column(Boolean, default=True, nullable=False)

    service        = relationship("Service", back_populates="utilisateurs")
    conversations  = relationship("Conversation", back_populates="utilisateur", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="utilisateur", cascade="all, delete-orphan")

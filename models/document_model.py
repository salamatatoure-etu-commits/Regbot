from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Document(Base):
    __tablename__ = "document"

    documentId    = Column(String, primary_key=True)
    name          = Column(String, nullable=False)
    source        = Column(String, nullable=False)
    last_modified = Column(DateTime, nullable=True)
    size          = Column(Float, nullable=True)
    mime_type     = Column(String, nullable=True)
    web_url       = Column(String, nullable=True)
    download_url  = Column(String, nullable=True)
    service_id    = Column(Integer, ForeignKey("service.serviceId"), nullable=True)

    service = relationship("Service", back_populates="documents")
    chunks  = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

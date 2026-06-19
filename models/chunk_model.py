from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .base import Base


class Chunk(Base):
    __tablename__ = "chunk"

    chunkId     = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String, ForeignKey("document.documentId", ondelete="CASCADE"), nullable=False)
    page_num    = Column(Integer, nullable=True)
    chunk_index = Column(Integer, nullable=False, default=0)
    contenu     = Column(Text, nullable=False)
    embedding   = Column(Vector(384), nullable=True)
    is_indexed  = Column(Boolean, default=False, nullable=False)
    created_at  = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    document = relationship("Document", back_populates="chunks")

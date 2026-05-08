from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentCreate(BaseModel):
    documentId: str
    name: str
    source: str
    service_id: Optional[int] = None
    last_modified: Optional[datetime] = None
    size: Optional[float] = None
    mime_type: Optional[str] = None
    web_url: Optional[str] = None
    download_url: Optional[str] = None


class DocumentOut(BaseModel):
    documentId: str
    name: str
    source: str
    service_id: Optional[int] = None
    last_modified: Optional[datetime] = None
    size: Optional[float] = None
    mime_type: Optional[str] = None
    web_url: Optional[str] = None
    download_url: Optional[str] = None

    class Config:
        from_attributes = True

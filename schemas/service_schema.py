from pydantic import BaseModel
from typing import Optional


class ServiceCreate(BaseModel):
    nom: str
    description: Optional[str] = None


class ServiceOut(BaseModel):
    serviceId: int
    nom: str
    description: Optional[str]

    class Config:
        from_attributes = True

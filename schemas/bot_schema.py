from pydantic import BaseModel
from typing import Optional
from models.bot_model import BotStatus


class BotCreate(BaseModel):
    nom: str
    service_id: int
    langue: str = "fr"
    llm_model_id: Optional[int] = None
    prompt: Optional[str] = None


class BotOut(BaseModel):
    botId: int
    nom: str
    service_id: Optional[int]
    langue: Optional[str]
    actif: Optional[bool]
    status: BotStatus
    llm_model_id: Optional[int]

    class Config:
        from_attributes = True

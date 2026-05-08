from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import Bot, Service, LLMModel
from schemas import BotOut
from schemas.bot_schema import BotCreate
from auth.dependencies import get_db

router = APIRouter(prefix="/bots", tags=["Bots"])


@router.get("/", response_model=List[BotOut])
def list_bots(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(Bot).offset(skip).limit(limit).all()


@router.get("/{bot_id}", response_model=BotOut)
def get_bot(bot_id: int, db: Session = Depends(get_db)):
    bot = db.query(Bot).filter(Bot.botId == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot non trouvé")
    return bot


@router.post("/", response_model=BotOut, status_code=201)
def create_bot(data: BotCreate, db: Session = Depends(get_db)):
    if not db.query(Service).filter(Service.serviceId == data.service_id).first():
        raise HTTPException(status_code=400, detail="Service introuvable")
    if data.llm_model_id and not db.query(LLMModel).filter(LLMModel.llmId == data.llm_model_id).first():
        raise HTTPException(status_code=400, detail="Modèle LLM introuvable")
    bot = Bot(**data.model_dump())
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot


@router.delete("/{bot_id}", status_code=204)
def delete_bot(bot_id: int, db: Session = Depends(get_db)):
    bot = db.query(Bot).filter(Bot.botId == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot non trouvé")
    db.delete(bot)
    db.commit()

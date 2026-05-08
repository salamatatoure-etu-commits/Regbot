from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import Message
from schemas import MessageCreate, MessageOut
from auth.dependencies import get_db

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.post("/", response_model=MessageOut, status_code=201)
def create_message(data: MessageCreate, db: Session = Depends(get_db)):
    msg = Message(**data.model_dump())
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.get("/{message_id}", response_model=MessageOut)
def get_message(message_id: int, db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.messageId == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message non trouvé")
    return msg


@router.patch("/{message_id}/feedback", response_model=MessageOut)
def evaluer_message(message_id: int, feedback: int, feedback_text: str = None, db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.messageId == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message non trouvé")
    if not (1 <= feedback <= 5):
        raise HTTPException(status_code=400, detail="Le feedback doit être entre 1 et 5")
    msg.feedback = feedback
    msg.feedback_text = feedback_text
    db.commit()
    db.refresh(msg)
    return msg


@router.delete("/{message_id}", status_code=204)
def delete_message(message_id: int, db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.messageId == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message non trouvé")
    db.delete(msg)
    db.commit()

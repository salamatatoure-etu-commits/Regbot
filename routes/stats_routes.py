from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, UTC, timedelta

from models import Utilisateur, Conversation
from models.service_model import Service
from models.message_model import Message
from models.enums import MessageTypeEnum
from auth.dependencies import get_db, require_admin

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/")
def get_stats(db: Session = Depends(get_db), _: Utilisateur = Depends(require_admin)):
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start  = now - timedelta(days=7)

    total_questions   = db.query(func.count(Message.messageId)).filter(Message.type_message == MessageTypeEnum.user).scalar() or 0
    questions_today   = db.query(func.count(Message.messageId)).filter(Message.type_message == MessageTypeEnum.user, Message.timestamp >= today_start).scalar() or 0
    questions_week    = db.query(func.count(Message.messageId)).filter(Message.type_message == MessageTypeEnum.user, Message.timestamp >= week_start).scalar() or 0
    total_convs       = db.query(func.count(Conversation.conversationid)).scalar() or 0
    active_convs      = db.query(func.count(Conversation.conversationid)).filter(Conversation.status == "active").scalar() or 0

    daily = db.query(
        func.date(Message.timestamp).label("date"),
        func.count(Message.messageId).label("count"),
    ).filter(
        Message.type_message == MessageTypeEnum.user,
        Message.timestamp >= week_start,
    ).group_by(func.date(Message.timestamp)).order_by(func.date(Message.timestamp)).all()

    return {
        "total_questions":   total_questions,
        "questions_today":   questions_today,
        "questions_week":    questions_week,
        "total_conversations": total_convs,
        "active_conversations": active_convs,
        "daily": [{"date": str(r.date), "count": r.count} for r in daily],
    }


@router.get("/by-service")
def stats_by_service(db: Session = Depends(get_db), _: Utilisateur = Depends(require_admin)):
    results = (
        db.query(Service.nom, func.count(Message.messageId).label("questions"))
        .join(Conversation, Conversation.service_id == Service.serviceId)
        .join(Message, Message.conversation_id == Conversation.conversationid)
        .filter(Message.type_message == MessageTypeEnum.user)
        .group_by(Service.serviceId, Service.nom)
        .order_by(func.count(Message.messageId).desc())
        .all()
    )
    return [{"service": r.nom, "questions": r.questions} for r in results]


@router.get("/logs")
def get_logs(limit: int = 50, db: Session = Depends(get_db), _: Utilisateur = Depends(require_admin)):
    msgs = db.query(Message).order_by(Message.timestamp.desc()).limit(limit).all()
    return [
        {
            "id":              m.messageId,
            "conversation_id": m.conversation_id,
            "type":            m.type_message,
            "content":         m.contenu[:120],
            "timestamp":       m.timestamp,
            "type_question":   m.type_question,
        }
        for m in msgs
    ]

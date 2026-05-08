from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import Bot

DEFAULT_PROMPT = (
    "Tu es un assistant interne d'entreprise. "
    "Réponds uniquement en te basant sur le contexte fourni. "
    "Si la réponse n'est pas dans le contexte, dis-le clairement."
)


def resolve_prompt_for_bot(db: Session, bot_id: int) -> str:
    """Retourne le prompt du bot s'il est défini, sinon le prompt par défaut."""
    bot = db.query(Bot).filter(Bot.botId == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot non trouvé")
    if bot.prompt and bot.prompt.strip():
        return bot.prompt.strip()
    return DEFAULT_PROMPT

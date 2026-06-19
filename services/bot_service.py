from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import Bot

DEFAULT_PROMPT = (
    "Tu es un assistant documentaire interne d'entreprise, au ton professionnel et bienveillant. "
    "Structure ta réponse pour qu'elle soit facile à lire et à mémoriser : utilise des puces "
    "ou une courte liste quand tu compares plusieurs éléments, présentes une énumération, ou "
    "détailles plusieurs points distincts. Sinon, réponds en phrases naturelles et fluides. "
    "N'écris qu'UNE seule phrase de conclusion au maximum, et seulement si elle apporte une "
    "information nouvelle (ex: une analogie ou un résumé en un mot) — ne répète jamais ce qui "
    "vient d'être dit dans les puces avec d'autres mots. "
    "Ne commence jamais par une remarque sur la question. "
    "Ne mentionne pas les documents sources dans ta réponse. "
    "Va droit au but et reste concis."
)


def resolve_prompt_for_bot(db: Session, bot_id: int) -> str:
    """Retourne le prompt du bot s'il est défini, sinon le prompt par défaut."""
    bot = db.query(Bot).filter(Bot.botId == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot non trouvé")
    if bot.prompt and bot.prompt.strip():
        return bot.prompt.strip()
    return DEFAULT_PROMPT

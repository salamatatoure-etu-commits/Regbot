import uuid
import logging
from datetime import datetime, UTC, timedelta

from sqlalchemy.orm import Session

from models import Document, Conversation, ConversationTempDocument
from models.conversation_model import ConversationStatus
from rag.indexer import index_document

logger = logging.getLogger("uvicorn")

MAX_DOCS_PER_CONVERSATION = 3
MAX_FILE_SIZE             = 10 * 1024 * 1024  # 10 MB
TTL_HOURS                 = 1


# ------------------------------------------------------------------ #
# UPLOAD                                                               #
# ------------------------------------------------------------------ #

def upload_temp_document(
    db: Session,
    conversation_id: int,
    filename: str,
    content_bytes: bytes,
    mime_type: str,
    utilisateur_id: int,
) -> ConversationTempDocument:
    # Vérification taille
    if len(content_bytes) > MAX_FILE_SIZE:
        raise ValueError(f"Fichier trop volumineux (max {MAX_FILE_SIZE // (1024*1024)} MB).")

    # Vérification limite documents actifs
    active_count = db.query(ConversationTempDocument).filter(
        ConversationTempDocument.conversation_id == conversation_id,
        ConversationTempDocument.expires_at > datetime.now(UTC),
    ).count()
    if active_count >= MAX_DOCS_PER_CONVERSATION:
        raise ValueError(f"Limite de {MAX_DOCS_PER_CONVERSATION} documents atteinte pour cette conversation.")

    # Récupérer le service_id depuis la conversation
    conv = db.query(Conversation).filter(
        Conversation.conversationid == conversation_id
    ).first()
    service_id = conv.service_id if conv else None

    # Créer un Document temporaire
    document_id = str(uuid.uuid4())
    doc = Document(
        documentId=document_id,
        name=filename,
        source="temp",
        service_id=service_id,
        mime_type=mime_type,
        size=round(len(content_bytes) / 1024, 2),
        last_modified=datetime.now(UTC),
    )
    db.add(doc)
    db.commit()

    # Indexer le document
    try:
        n = index_document(db, document_id, content_bytes, mime_type)
        logger.info(f"Temp doc {document_id} : {n} chunks indexés.")
    except Exception as e:
        logger.error(f"Indexation temp doc {document_id} échouée : {e}")

    # Créer l'entrée ConversationTempDocument (filepath = document_id)
    expires_at = datetime.now(UTC) + timedelta(hours=TTL_HOURS)
    temp_doc = ConversationTempDocument(
        conversation_id=conversation_id,
        filename=filename,
        filepath=document_id,
        uploaded_at=datetime.now(UTC),
        expires_at=expires_at,
        uploaded_by=utilisateur_id,
    )
    db.add(temp_doc)
    db.commit()
    db.refresh(temp_doc)
    return temp_doc


# ------------------------------------------------------------------ #
# LECTURE                                                              #
# ------------------------------------------------------------------ #

def get_active_document_ids(db: Session, conversation_id: int) -> list[str]:
    """Retourne les document_ids des docs temporaires actifs pour une conversation."""
    temp_docs = db.query(ConversationTempDocument).filter(
        ConversationTempDocument.conversation_id == conversation_id,
        ConversationTempDocument.expires_at > datetime.now(UTC),
    ).all()
    return [td.filepath for td in temp_docs if td.filepath]


def list_temp_documents(db: Session, conversation_id: int) -> list[dict]:
    temp_docs = db.query(ConversationTempDocument).filter(
        ConversationTempDocument.conversation_id == conversation_id,
    ).all()
    return [
        {
            "id": td.id,
            "filename": td.filename,
            "uploaded_at": td.uploaded_at,
            "expires_at": td.expires_at,
            "actif": td.expires_at > datetime.now(UTC) if td.expires_at else False,
        }
        for td in temp_docs
    ]


# ------------------------------------------------------------------ #
# NETTOYAGE                                                            #
# ------------------------------------------------------------------ #

def cleanup_expired_documents(db: Session) -> int:
    """Supprime les documents temporaires expirés (Document + chunks + entrée temp)."""
    expired = db.query(ConversationTempDocument).filter(
        ConversationTempDocument.expires_at <= datetime.now(UTC),
    ).all()

    count = 0
    for td in expired:
        if td.filepath:
            doc = db.query(Document).filter(Document.documentId == td.filepath).first()
            if doc:
                db.delete(doc)
        db.delete(td)
        count += 1

    db.commit()
    logger.info(f"Cleanup : {count} documents temporaires supprimés.")
    return count


def cleanup_expired_db_entries(db: Session) -> int:
    """Supprime les entrées temp expirées depuis plus de 30 jours."""
    threshold = datetime.now(UTC) - timedelta(days=30)
    old = db.query(ConversationTempDocument).filter(
        ConversationTempDocument.expires_at <= threshold,
    ).all()
    for td in old:
        db.delete(td)
    db.commit()
    return len(old)


# ------------------------------------------------------------------ #
# CONVERSATIONS EXPIRÉES                                               #
# ------------------------------------------------------------------ #

INACTIVITY_HOURS = 24


def mark_expired_conversations(db: Session) -> int:
    """Ferme les conversations inactives depuis plus de INACTIVITY_HOURS heures."""
    threshold = datetime.now(UTC) - timedelta(hours=INACTIVITY_HOURS)
    expired = db.query(Conversation).filter(
        Conversation.last_activity <= threshold,
        Conversation.status == ConversationStatus.active,
    ).all()
    for conv in expired:
        conv.status = ConversationStatus.closed
        conv.end_time = datetime.now(UTC)
    db.commit()
    logger.info(f"{len(expired)} conversations fermées.")
    return len(expired)

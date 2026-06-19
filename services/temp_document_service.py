import uuid
import logging
from datetime import datetime, UTC, timedelta

from sqlalchemy.orm import Session

from models import Document, Conversation, ConversationTempDocument
from models.conversation_model import ConversationStatus
from models.base import SessionLocal
from rag.indexer import index_document

logger = logging.getLogger("uvicorn")

MAX_DOCS_PER_CONVERSATION = 3
MAX_FILE_SIZE             = 50 * 1024 * 1024  # 50 MB

# expires_at n'est plus utilisé comme TTL fonctionnel : la durée de vie d'un
# document temporaire suit désormais le statut de la conversation (active/closed).
# La colonne reste NOT NULL en base, on y met donc une valeur sentinelle lointaine.
_SENTINEL_EXPIRES_AT_YEARS = 10


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

    # Récupérer la conversation et la rouvrir si elle avait été fermée
    conv = db.query(Conversation).filter(
        Conversation.conversationid == conversation_id
    ).first()
    if conv and conv.status == ConversationStatus.closed:
        conv.status = ConversationStatus.active
        conv.end_time = None
        db.commit()
    service_id = conv.service_id if conv else None

    # Vérification limite documents actifs (tous les docs encore présents pour
    # une conversation active sont considérés actifs)
    active_count = db.query(ConversationTempDocument).filter(
        ConversationTempDocument.conversation_id == conversation_id,
    ).count()
    if active_count >= MAX_DOCS_PER_CONVERSATION:
        raise ValueError(f"Limite de {MAX_DOCS_PER_CONVERSATION} documents atteinte pour cette conversation.")

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

    # Créer l'entrée ConversationTempDocument (filepath = document_id)
    # L'indexation (extraction + chunking + embeddings) se fait en tâche de
    # fond (cf. index_temp_document_background) pour ne pas bloquer la requête.
    expires_at = datetime.now(UTC) + timedelta(days=365 * _SENTINEL_EXPIRES_AT_YEARS)
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


def index_temp_document_background(document_id: str, content_bytes: bytes, mime_type: str):
    """Indexe un document temporaire en arrière-plan (appelé via BackgroundTasks).

    Utilise sa propre session DB car la session de la requête HTTP est déjà fermée
    quand cette fonction s'exécute.
    """
    db = SessionLocal()
    try:
        n = index_document(db, document_id, content_bytes, mime_type)
        if n == 0:
            logger.warning(f"Temp doc {document_id} : aucun chunk extrait, document supprimé.")
            doc = db.query(Document).filter(Document.documentId == document_id).first()
            if doc:
                db.delete(doc)
            td = db.query(ConversationTempDocument).filter(ConversationTempDocument.filepath == document_id).first()
            if td:
                db.delete(td)
            db.commit()
        else:
            logger.info(f"Temp doc {document_id} : {n} chunks indexés.")
    except Exception as e:
        logger.error(f"Indexation temp doc {document_id} échouée : {e}")
        try:
            doc = db.query(Document).filter(Document.documentId == document_id).first()
            if doc:
                db.delete(doc)
            td = db.query(ConversationTempDocument).filter(ConversationTempDocument.filepath == document_id).first()
            if td:
                db.delete(td)
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ------------------------------------------------------------------ #
# LECTURE                                                              #
# ------------------------------------------------------------------ #

def get_active_document_ids(db: Session, conversation_id: int) -> list[str]:
    """Retourne les document_ids des docs temporaires actifs pour une conversation.

    Un document temporaire est actif tant que sa conversation est active ;
    il cesse d'être pris en compte dès que la conversation est fermée.
    """
    temp_docs = (
        db.query(ConversationTempDocument)
        .join(Conversation, Conversation.conversationid == ConversationTempDocument.conversation_id)
        .filter(
            ConversationTempDocument.conversation_id == conversation_id,
            Conversation.status == ConversationStatus.active,
        )
        .all()
    )
    return [td.filepath for td in temp_docs if td.filepath]


def list_temp_documents(db: Session, conversation_id: int) -> list[dict]:
    conv = db.query(Conversation).filter(Conversation.conversationid == conversation_id).first()
    is_active = bool(conv and conv.status == ConversationStatus.active)
    temp_docs = db.query(ConversationTempDocument).filter(
        ConversationTempDocument.conversation_id == conversation_id,
    ).all()
    return [
        {
            "id": td.id,
            "filename": td.filename,
            "uploaded_at": td.uploaded_at,
            "expires_at": td.expires_at,
            "actif": is_active,
        }
        for td in temp_docs
    ]


# ------------------------------------------------------------------ #
# NETTOYAGE                                                            #
# ------------------------------------------------------------------ #

def cleanup_expired_documents(db: Session) -> int:
    """Supprime les documents temporaires des conversations fermées (Document + chunks + entrée temp).

    À appeler après mark_expired_conversations() afin que les conversations
    venant juste d'être fermées soient bien prises en compte dans la même passe.
    """
    expired = (
        db.query(ConversationTempDocument)
        .join(Conversation, Conversation.conversationid == ConversationTempDocument.conversation_id)
        .filter(Conversation.status == ConversationStatus.closed)
        .all()
    )

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
